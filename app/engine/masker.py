import re
from pathlib import Path
from typing import List, Tuple

import yaml

from app.models.report import HitDetail
from app.engine.dictionary_loader import DictionaryMasker


class MaskingEngine:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.regex_rules = self._load_regex_rules()
        self.dictionary_masker = DictionaryMasker(config_dir)

    def _load_regex_rules(self):
        rules_path = self.config_dir / "rules.yaml"
        if not rules_path.exists():
            return {}
        config = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
        regex_rules = config.get("regex_rules") or {}
        if not isinstance(regex_rules, dict):
            return {}
        return regex_rules

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

    def desensitize_text(self, text: str, location: str) -> Tuple[str, List[HitDetail]]:
        masked_text = text
        details: List[HitDetail] = []

        for rule_name, rule in self.regex_rules.items():
            pattern = rule.get("pattern")
            if not pattern:
                continue

            for match in list(re.finditer(pattern, masked_text)):
                original = match.group(0)
                replaced = self._mask_by_rule(rule_name, original)
                masked_text = masked_text.replace(original, replaced, 1)
                details.append(HitDetail(
                    entity_type=rule_name.upper(),
                    rule_type="regex",
                    location=location,
                    original_preview=original,
                    masked_preview=replaced,
                    confidence=1.0,
                    masked_by=f"{rule_name}_mask_v1"
                ))

        dict_matches = self.dictionary_masker.extract(masked_text)
        for keyword, start, end in reversed(dict_matches):
            replaced = "*" * len(keyword)
            masked_text = masked_text[:start] + replaced + masked_text[end:]
            details.append(HitDetail(
                entity_type="DICTIONARY_TERM",
                rule_type="dictionary",
                location=location,
                original_preview=keyword,
                masked_preview=replaced,
                confidence=1.0,
                masked_by="dictionary_mask_v1"
            ))

        return masked_text, details
