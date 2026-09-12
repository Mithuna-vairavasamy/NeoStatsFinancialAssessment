from pathlib import Path

from backend.app.services.document_validation_service import (
    DocumentValidationService,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_supported_pdf():
    service = DocumentValidationService()

    file_path = (
        PROJECT_ROOT
        / "F:\\project\\New Dataset 1\\New Dataset\\Balance Sheet\\Consolidated Balance Sheet 2017.pdf"
    )

    result = service.validate(str(file_path))

    assert result["is_supported"] is True
    assert result["is_readable"] is True
    assert result["page_count"] <= 3
    assert result["status"] == "PASS"


def test_unsupported_file_type(tmp_path):
    service = DocumentValidationService()

    file_path = tmp_path / "test.txt"
    file_path.write_text("invalid document")

    result = service.validate(str(file_path))

    assert result["is_supported"] is False
    assert result["status"] != "PASS"


def test_empty_file(tmp_path):
    service = DocumentValidationService()

    file_path = tmp_path / "empty.pdf"
    file_path.write_bytes(b"")

    result = service.validate(str(file_path))

    assert result["is_readable"] is False
    assert result["status"] != "PASS"