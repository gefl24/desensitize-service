import tempfile
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


def resolve_writable_dir(preferred: Path, fallback_name: str) -> Path:
    preferred = preferred.resolve()
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except Exception:
        fallback_root = Path(tempfile.gettempdir()) / "desensitize_service" / fallback_name
        fallback_root.mkdir(parents=True, exist_ok=True)
        return fallback_root
