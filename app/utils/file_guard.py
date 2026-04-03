from pathlib import Path

ALLOWED_EXTENSIONS = {".txt", ".md", ".docx", ".xlsx"}
MAX_FILE_SIZE = 20 * 1024 * 1024


def is_allowed_filename(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"unsupported file type: {suffix}")
    return suffix
