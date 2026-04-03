from pathlib import Path
from zipfile import BadZipFile, ZipFile

_ALLOWED_MAGIC = {
    '.txt': None,
    '.md': None,
    '.docx': 'zip',
    '.xlsx': 'zip',
}


def validate_file_signature(file_path: Path) -> bool:
    suffix = file_path.suffix.lower()
    expected = _ALLOWED_MAGIC.get(suffix)

    if expected is None:
        return True

    if expected == 'zip':
        try:
            with ZipFile(file_path, 'r') as zf:
                names = set(zf.namelist())
                if suffix == '.docx':
                    return '[Content_Types].xml' in names and any(name.startswith('word/') for name in names)
                if suffix == '.xlsx':
                    return '[Content_Types].xml' in names and any(name.startswith('xl/') for name in names)
        except BadZipFile:
            return False

    return False
