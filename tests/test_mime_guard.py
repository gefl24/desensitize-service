from pathlib import Path

from app.utils.mime_guard import validate_file_signature


def test_validate_text_file_signature(tmp_path: Path):
    path = tmp_path / 'sample.txt'
    path.write_text('hello', encoding='utf-8')
    assert validate_file_signature(path) is True


def test_reject_fake_docx_signature(tmp_path: Path):
    path = tmp_path / 'fake.docx'
    path.write_text('not a zip', encoding='utf-8')
    assert validate_file_signature(path) is False
