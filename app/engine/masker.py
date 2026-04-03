import re
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from app.engine.dictionary_loader import DictionaryMasker
from app.models.report import HitDetail


class MaskingEngine:
    def __init__(self, config_dir: Path, profile: str = "light"):
        self.config_dir = config_dir
        self.profile = profile or "light"
        self.config = self._load_config()
        self.regex_rules = self._load_regex_rules()
        self.person_context_rules = self._load_person_context_rules()
        self.org_suffix_rules = self._load_org_suffix_rules()
        self.dictionary_masker = DictionaryMasker(config_dir, config=self.config)

    def _load_config(self) -> Dict:
        rules_path = self.config_dir / "rules.yaml"
        if not rules_path.exists():
            return {}

        full_config = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
        profiles = full_config.get("profiles") or {}
        if not isinstance(profiles, dict) or self.profile not in profiles:
            return full_config

        base_config = {k: v for k, v in full_config.items() if k != "profiles"}
        profile_config = profiles.get(self.profile) or {}
        if not isinstance(profile_config, dict):
            return base_config

        merged = dict(base_config)
        merged.update(profile_config)
        return merged

    def _load_regex_rules(self) -> Dict:
        regex_rules = self.config.get("regex_rules") or {}
        return regex_rules if isinstance(regex_rules, dict) else {}

    def _load_person_context_rules(self) -> List[Dict]:
        rules = self.config.get("person_context_rules") or []
        return rules if isinstance(rules, list) else []

    def _load_org_suffix_rules(self) -> Dict:
        rules = self.config.get("org_suffix_rules") or {}
        return rules if isinstance(rules, dict) else {}

    def _mask_person_name(self, value: str) -> str:
        if len(value) <= 1:
            return "*"
        if len(value) == 2:
            return "*" + value[-1]
        return value[0] + "*" * (len(value) - 2) + value[-1]

    def _mask_org_name(self, value: str) -> str:
        keep_prefix_length = int(self.org_suffix_rules.get("keep_prefix_length", 5) or 5)
        visible_count = min(keep_prefix_length, max(1, len(value) - 1))
        visible_prefix = value[:visible_count]
        return visible_prefix + "*" * max(1, len(value) - visible_count)

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

    def _normalize_person_name(self, value: str, right_contexts: List[str]) -> str:
        candidate = value.strip()
        trailing_tokens = list(right_contexts) + [
            "跟进", "负责", "处理", "确认", "回复", "对接", "沟通", "审批", "已确认"
        ]
        for token in sorted(set(filter(None, trailing_tokens)), key=len, reverse=True):
            if candidate.endswith(token) and len(candidate) > len(token):
                candidate = candidate[:-len(token)]
                break

        invalid_first_chars = {"人", "方", "由", "员", "客"}
        invalid_last_chars = {"跟", "已", "来", "在", "做", "发"}

        while candidate and candidate[0] in invalid_first_chars:
            candidate = candidate[1:]
        while candidate and candidate[-1] in invalid_last_chars:
            candidate = candidate[:-1]
        return candidate

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
            left_name_max_length = int(rule.get("left_name_max_length", min(3, max_name_length)) or min(3, max_name_length))
            masked_by = rule.get("masked_by") or "person_context_mask_v2"
            confidence = float(rule.get("confidence", 0.85) or 0.85)

            for left in left_contexts:
                if not left:
                    continue
                pattern = re.escape(left) + rf"([\u4e00-\u9fff]{{2,{left_name_max_length}}})"
                for match in re.finditer(pattern, text):
                    raw_name = match.group(1)
                    name = self._normalize_person_name(raw_name, right_contexts)
                    if len(name) < 2:
                        continue
                    matches.append({
                        "start": match.start(1) + (len(raw_name) - len(name)),
                        "end": match.start(1) + len(raw_name),
                        "replacement": self._mask_person_name(name),
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
                    raw_name = match.group(1)
                    name = self._normalize_person_name(raw_name, right_contexts)
                    if len(name) < 2:
                        continue
                    matches.append({
                        "start": match.start(1) + (len(raw_name) - len(name)),
                        "end": match.start(1) + len(raw_name),
                        "replacement": self._mask_person_name(name),
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

        skip_tokens = set(self.org_suffix_rules.get("skip_tokens") or [
            "来自", "员工", "联系人", "客户", "对接人", "负责人", "由", "在", "是"
        ])
        role_prefixes = ["合作方", "甲方", "乙方", "客户", "供应商"]

        matches: List[Dict] = []
        for suffix in suffixes:
            if not suffix:
                continue
            pattern = rf"([\u4e00-\u9fffA-Za-z0-9]{{2,{max_prefix_length}}}{re.escape(suffix)})"
            for match in re.finditer(pattern, text):
                org_name = match.group(1)
                start = match.start(1)
                end = match.end(1)

                split_pattern = "|".join(re.escape(token) for token in skip_tokens if token)
                if split_pattern:
                    candidate_parts = re.split(split_pattern, org_name)
                    candidate = candidate_parts[-1] if candidate_parts else org_name
                    if candidate and candidate != org_name:
                        start = end - len(candidate)
                        org_name = candidate

                for prefix in role_prefixes:
                    if org_name.startswith(prefix) and len(org_name) > len(prefix):
                        org_name = org_name[len(prefix):]
                        start = end - len(org_name)
                        break

                if not org_name:
                    continue

                end = start + len(org_name)
                replacement = self._mask_org_name(org_name)
                matches.append({
                    "start": start,
                    "end": end,
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
            "regex": 5,
            "person_context": 4,
            "org_suffix": 4,
            "dictionary_group": 3,
            "dictionary": 2,
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
            entity_type = payload.get("entity_type", "DICTIONARY_TERM")
            if entity_type == "PERSON_NAME":
                replaced = self._mask_person_name(keyword)
            elif entity_type == "ORGANIZATION_NAME":
                replaced = self._mask_org_name(keyword)
            else:
                replaced = "*" * len(keyword)
            all_matches.append({
                "start": start,
                "end": end,
                "replacement": replaced,
                "entity_type": entity_type,
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
