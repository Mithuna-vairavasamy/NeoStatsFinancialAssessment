from pathlib import Path

from backend.app.services.extraction_service import (
    ExtractionService,
)


def test_extract_invoice_image():
    service = ExtractionService()

    file_path = Path(
        r"F:\project\New Dataset 1\New Dataset\Invoices\20251118_000612.jpg"
    )

    result = service.extract(str(file_path))

    assert result["text"]
    assert result["pages"]
    assert result["extraction_method"]
    assert result["ocr_used"] is True
    assert result["confidence"] is not None


def test_extract_balance_sheet_pdf():
    service = ExtractionService()

    file_path = Path(
        r"F:\project\New Dataset 1\New Dataset\Balance Sheet\Consolidated Balance Sheet 2017.pdf"
    )

    result = service.extract(str(file_path))

    assert result["text"]
    assert result["pages"]
    assert result["extraction_method"]
    assert result["ocr_used"] is not None
    assert result["confidence"] is not None


def test_extract_cash_flow_pdf():
    service = ExtractionService()

    file_path = Path(
        r"F:\project\New Dataset 1\New Dataset\Cash Flows\Consolidated Cash Flow Statement 2017.pdf"
    )

    result = service.extract(str(file_path))

    assert result["text"]
    assert result["pages"]
    assert result["extraction_method"]
    assert result["ocr_used"] is not None
    assert result["confidence"] is not None