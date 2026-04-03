from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def build_result_zip(zip_path: Path, masked_file: Path, report_file: Path) -> Path:
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        zf.write(masked_file, arcname=masked_file.name)
        zf.write(report_file, arcname=report_file.name)
    return zip_path
