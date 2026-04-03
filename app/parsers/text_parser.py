from pathlib import Path
from typing import List, Tuple

from app.engine.masker import MaskingEngine
from app.models.report import HitDetail


def process_text_file(file_path: Path, output_path: Path, engine: MaskingEngine) -> Tuple[Path, List[HitDetail]]:
    text = file_path.read_text(encoding="utf-8")
    masked_text, details = engine.desensitize_text(text, location="text:1")
    output_path.write_text(masked_text, encoding="utf-8")
    return output_path, details
