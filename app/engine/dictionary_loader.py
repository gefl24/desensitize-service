from pathlib import Path
from typing import Dict, List, Tuple

import yaml

try:
    from flashtext import KeywordProcessor  # type: ignore
except ImportError:  # pragma: no cover
    KeywordProcessor = None


class _SimpleKeywordProcessor:
    def __init__(self, case_sensitive: bool = False):
        self.case_sensitive = case_sensitive
        self._keywords: List[Tuple[str, Dict[str, str]]] = []

    def add_keyword(self, keyword: str, payload: Dict[str, str]) -> None:
        self._keywords.append((keyword, payload))

    def extract_keywords(self, text: str, span_info: bool = True):
        haystack = text if self.case_sensitive else text.lower()
        matches = []
        for keyword, payload in self._keywords:
            needle = keyword if self.case_sensitive else keyword.lower()
            start = 0
            while True:
                index = haystack.find(needle, start)
                if index == -1:
                    break
                matches.append((payload, index, index + len(keyword)))
                start = index + len(keyword)
        matches.sort(key=lambda item: (item[1], -(item[2] - item[1])))
        return matches


class DictionaryMasker:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        processor_cls = KeywordProcessor or _SimpleKeywordProcessor
        self.keyword_processor = processor_cls(case_sensitive=False)
        self.loaded_keywords: List[str] = []
        self._load()

    def _load_lines(self, dict_name: str) -> List[str]:
        dict_path = self.config_dir / "dictionaries" / dict_name
        if not dict_path.exists():
            return []
        return [line.strip() for line in dict_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _register_keywords(self, dict_files: List[str], group: str, entity_type: str, rule_type: str, masked_by: str) -> None:
        for dict_name in dict_files:
            for keyword in self._load_lines(dict_name):
                payload = {
                    "keyword": keyword,
                    "group": group,
                    "entity_type": entity_type,
                    "rule_type": rule_type,
                    "masked_by": masked_by,
                }
                self.keyword_processor.add_keyword(keyword, payload)
                self.loaded_keywords.append(keyword)

    def _load(self) -> None:
        rules_path = self.config_dir / "rules.yaml"
        if not rules_path.exists():
            return

        config = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}

        dictionary_groups = config.get("dictionary_groups") or {}
        if isinstance(dictionary_groups, dict):
            for group_name, dict_files in dictionary_groups.items():
                if not isinstance(dict_files, list):
                    continue
                normalized_group = str(group_name).strip().lower() or "default"
                if normalized_group in {"person", "people", "name", "names"}:
                    entity_type = "PERSON_NAME"
                elif normalized_group in {"org", "organization", "company", "companies"}:
                    entity_type = "ORGANIZATION_NAME"
                else:
                    entity_type = f"DICTIONARY_{normalized_group.upper()}"
                self._register_keywords(
                    dict_files=dict_files,
                    group=normalized_group,
                    entity_type=entity_type,
                    rule_type="dictionary_group",
                    masked_by=f"dictionary_{normalized_group}_mask_v2",
                )

        dictionary_files = config.get("dictionary_files") or []
        if isinstance(dictionary_files, list):
            self._register_keywords(
                dict_files=dictionary_files,
                group="default",
                entity_type="DICTIONARY_TERM",
                rule_type="dictionary",
                masked_by="dictionary_mask_v1",
            )

    def extract(self, text: str) -> List[Tuple[Dict[str, str], int, int]]:
        return self.keyword_processor.extract_keywords(text, span_info=True)
