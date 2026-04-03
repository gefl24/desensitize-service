from pathlib import Path
from typing import Tuple, List

from app.engine.masker import MaskingEngine
from app.models.report import HitDetail
from app.parsers.docx_parser import process_docx
from app.parsers.text_parser import process_text_file
from app.parsers.xlsx_parser import process_xlsx


class FileDispatcher:
    def __init__(self, engine: MaskingEngine):
        self.engine = engine

    def dispatch(self, file_path: Path, output_path: Path) -> Tuple[Path, List[HitDetail]]:
        suffix = file_path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return process_text_file(file_path, output_path, self.engine)
        if suffix == ".docx":
            return process_docx(file_path, output_path, self.engine)
        if suffix == ".xlsx":
            return process_xlsx(file_path, output_path, self.engine)
        raise ValueError(f"unsupported suffix: {suffix}")
