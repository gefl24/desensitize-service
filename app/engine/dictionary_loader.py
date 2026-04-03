from pathlib import Path
from flashtext import KeywordProcessor
import yaml


class DictionaryMasker:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.keyword_processor = KeywordProcessor(case_sensitive=False)
        self.loaded_keywords = []
        self._load()

    def _load(self) -> None:
        rules_path = self.config_dir / "rules.yaml"
        if not rules_path.exists():
            return

        config = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
        for dict_name in config.get("dictionary_files", []):
            dict_path = self.config_dir / "dictionaries" / dict_name
            if not dict_path.exists():
                continue
            for raw in dict_path.read_text(encoding="utf-8").splitlines():
                keyword = raw.strip()
                if not keyword:
                    continue
                self.keyword_processor.add_keyword(keyword, keyword)
                self.loaded_keywords.append(keyword)

    def extract(self, text: str):
        return self.keyword_processor.extract_keywords(text, span_info=True)
