import re
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from app.models.report import HitDetail
from app.engine.dictionary_loader import DictionaryMasker


class MaskingEngine:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config = self._load_config()
        self.regex_rules = self._load_regex_rules()
        self.person_context_rules = self._load_person_context_rules()
        self.org_suffix_rules = self._load_org_suffix_rules()
        self.dictionary_masker = DictionaryMasker(config_dir)

    def _load_config(self) -> Dict:
        rules_path = self.config_dir / "rules.yaml"
        if not rules_path.exists():
            return {}
        return yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}

    def _load_regex_rules(self):
        regex_rules = self.config.get("regex_rules") or {}
        if not isinstance(regex_rules, dict):
            return {}
        return regex_rules

    def _load_person_context_rules(self):
        rules = self.config.get("person_context_rules") or []
        return rules if isinstance(rules, list) else []

    def _load_org_suffix_rules(self):
        rules = self.config.get("org_suffix_rules") or {}
        return rules if isinstance(rules, dict) else {}

    def _mask_by_rule(self, rule_name: str, value: str) -> str:
        if rule_name == "phone":
            return value[:3] + "****" + value[-4:]
        if rule_name == "email":
            parts = value.split("@", 1)
            if len(parts) == 2:
                local = parts[0]
                masked_local = local[:2] + "***" if len(local) > 2 else "***"
                return masked_local + "@" + parts[1]
        if rule_name == "id_card":
            match = re.match(r'(\d{6})\d{8}(\d{3}[0-9Xx])', value)
            if match:
                return f"{match.group(1)}********{match.group(2)}"
        if rule_name == "bank_card":
            if len(value) >= 8:
                return value[:4] + "*" * (len(value) - 8) + value[-4:]
        return "[MASKED]"

    def _apply_matches(self, text: str, matches: List[Dict]) -> Tuple[str, List[HitDetail]]:
        if not matches:
            return text, []

        masked_text = text
        details: List[HitDetail] = []
        for item in sorted(matches, key=lambda x: x["start"], reverse=True):
            start = item["start"]
            end = item["end"]
            original = masked_text[start:end]
            replacement = item["replacement"]
            masked_text = masked_text[:start] + replacement + masked_text[end:]
            details.append(HitDetail(
                entity_type=item["entity_type"],
                rule_type=item["rule_type"],
                location=item["location"],
                original_preview=original,
                masked_preview=replacement,
                confidence=item.get("confidence", 1.0),
                masked_by=item.get("masked_by"),
            ))
        return masked_text, details

    def _extract_person_context_matches(self, text: str, location: str) -> List[Dict]:
        matches: List[Dict] = []
        for rule in self.person_context_rules:
            left_contexts = rule.get("left_contexts") or []
            right_contexts = rule.get("right_contexts") or []
            max_name_length = int(rule.get("max_name_length", 4) or 4)
            masked_by = rule.get("masked_by") or "person_context_mask_v2"
            confidence = float(rule.get("confidence", 0.85) or 0.85)

            for left in left_contexts:
                if not left:
                    continue
                pattern = re.escape(left) + rf"([\u4e00-\u9fff]{{2,{max_name_length}}})"
                for match in re.finditer(pattern, text):
                    name = match.group(1)
                    matches.append({
                        "start": match.start(1),
                        "end": match.end(1),
                        "replacement": name[0] + "*" * (len(name) - 1),
                        "entity_type": "PERSON_NAME",
                        "rule_type": "person_context",
                        "location": location,
                        "confidence": confidence,
                        "masked_by": masked_by,
                    })

            for right in right_contexts:
                if not right:
                    continue
                pattern = rf"([\u4e00-\u9fff]{{2,{max_name_length}}})" + re.escape(right)
                for match in re.finditer(pattern, text):
                    name = match.group(1)
                    matches.append({
                        "start": match.start(1),
                        "end": match.end(1),
                        "replacement": name[0] + "*" * (len(name) - 1),
                        "entity_type": "PERSON_NAME",
                        "rule_type": "person_context",
                        "location": location,
                        "confidence": confidence,
                        "masked_by": masked_by,
                    })
        return matches

    def _extract_org_suffix_matches(self, text: str, location: str) -> List[Dict]:
        suffixes = self.org_suffix_rules.get("suffixes") or []
        max_prefix_length = int(self.org_suffix_rules.get("max_prefix_length", 16) or 16)
        confidence = float(self.org_suffix_rules.get("confidence", 0.8) or 0.8)
        masked_by = self.org_suffix_rules.get("masked_by") or "org_suffix_mask_v2"
        if not isinstance(suffixes, list):
            return []

        matches: List[Dict] = []
        for suffix in suffixes:
            if not suffix:
                continue
            pattern = rf"([\u4e00-\u9fffA-Za-z0-9]{{2,{max_prefix_length}}}{re.escape(suffix)})"
            for match in re.finditer(pattern, text):
                org_name = match.group(1)
                replacement = org_name[:2] + "*" * max(1, len(org_name) - 2)
                matches.append({
                    "start": match.start(1),
                    "end": match.end(1),
                    "replacement": replacement,
                    "entity_type": "ORGANIZATION_NAME",
                    "rule_type": "org_suffix",
                    "location": location,
                    "confidence": confidence,
                    "masked_by": masked_by,
                })
        return matches

    def _dedupe_overlaps(self, matches: List[Dict]) -> List[Dict]:
        if not matches:
            return []

        priority = {
            "regex": 4,
            "dictionary_group": 3,
            "dictionary": 2,
            "person_context": 1,
            "org_suffix": 1,
        }
        ordered = sorted(
            matches,
            key=lambda x: (
                x["start"],
                -(x["end"] - x["start"]),
                -priority.get(x["rule_type"], 0),
            )
        )

        selected: List[Dict] = []
        occupied = []
        for item in ordered:
            overlap = any(not (item["end"] <= start or item["start"] >= end) for start, end in occupied)
            if overlap:
                continue
            selected.append(item)
            occupied.append((item["start"], item["end"]))
        return selected

    def desensitize_text(self, text: str, location: str) -> Tuple[str, List[HitDetail]]:
        all_matches: List[Dict] = []

        for rule_name, rule in self.regex_rules.items():
            pattern = rule.get("pattern")
            if not pattern:
                continue
            for match in re.finditer(pattern, text):
                original = match.group(0)
                replaced = self._mask_by_rule(rule_name, original)
                all_matches.append({
                    "start": match.start(),
                    "end": match.end(),
                    "replacement": replaced,
                    "entity_type": rule_name.upper(),
                    "rule_type": "regex",
                    "location": location,
                    "confidence": 1.0,
                    "masked_by": f"{rule_name}_mask_v1",
                })

        dict_matches = self.dictionary_masker.extract(text)
        for payload, start, end in dict_matches:
            keyword = payload["keyword"]
            replaced = "*" * len(keyword)
            all_matches.append({
                "start": start,
                "end": end,
                "replacement": replaced,
                "entity_type": payload.get("entity_type", "DICTIONARY_TERM"),
                "rule_type": payload.get("rule_type", "dictionary"),
                "location": location,
                "confidence": 1.0,
                "masked_by": payload.get("masked_by", "dictionary_mask_v1"),
            })

        all_matches.extend(self._extract_person_context_matches(text, location))
        all_matches.extend(self._extract_org_suffix_matches(text, location))

        deduped = self._dedupe_overlaps(all_matches)
        masked_text, details = self._apply_matches(text, deduped)
        return masked_text, details
