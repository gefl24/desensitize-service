from datetime import datetime, timedelta
from pathlib import Path


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def cleanup_expired_files(*directories: Path, ttl_hours: int = 24) -> int:
    cutoff = datetime.now() - timedelta(hours=ttl_hours)
    removed = 0
    for directory in directories:
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if not path.is_file():
                continue
            modified = datetime.fromtimestamp(path.stat().st_mtime)
            if modified < cutoff:
                path.unlink(missing_ok=True)
                removed += 1
    return removed
