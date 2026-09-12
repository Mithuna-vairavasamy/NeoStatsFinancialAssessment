from pathlib import Path
from typing import Any

import pymupdf


class DocumentValidationService:
    """
    Validates uploaded documents before text extraction/OCR.

    Supported formats:
    - PDF
    - JPG
    - JPEG
    - PNG

    PDF limit:
    - Maximum 3 pages
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
    MAX_PDF_PAGES = 3

    def validate(
        self,
        file_path: str,
        original_filename: str | None = None,
    ) -> dict[str, Any]:
        """
        Validate a document.

        Returns a structured validation result.
        """

        path = Path(file_path)

        filename = original_filename or path.name
        extension = path.suffix.lower()

        result = {
            "file_name": filename,
            "file_type": extension.replace(".", "").upper(),
            "is_supported": False,
            "is_readable": False,
            "page_count": None,
            "status": "FAILED",
            "error_code": None,
            "error_message": None,
        }


        if not path.exists():
            result["error_code"] = "FILE_NOT_FOUND"
            result["error_message"] = "The uploaded file was not found."
            return result


        if path.stat().st_size == 0:
            result["error_code"] = "EMPTY_FILE"
            result["error_message"] = "The uploaded file is empty."
            return result


        if extension not in self.SUPPORTED_EXTENSIONS:
            result["error_code"] = "UNSUPPORTED_FILE_TYPE"
            result["error_message"] = (
                "Only PDF / JPG / PNG documents are supported."
            )
            return result

        result["is_supported"] = True


        if extension == ".pdf":
            return self._validate_pdf(path, result)


        return self._validate_image(path, result)

    def _validate_pdf(
        self,
        path: Path,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate PDF readability and page count.
        """

        document = None

        try:
            document = pymupdf.open(str(path))

            page_count = document.page_count
            result["page_count"] = page_count

            # Empty PDF
            if page_count == 0:
                result["error_code"] = "EMPTY_PDF"
                result["error_message"] = (
                    "The PDF does not contain any pages."
                )
                return result

            # Maximum 3 pages
            if page_count > self.MAX_PDF_PAGES:
                result["error_code"] = "PAGE_LIMIT_EXCEEDED"
                result["error_message"] = (
                    f"PDF contains {page_count} pages. "
                    f"Maximum allowed is {self.MAX_PDF_PAGES} pages."
                )
                return result

            # Try loading every page to make sure the document is readable.
            for page_number in range(page_count):
                document.load_page(page_number)

            result["is_readable"] = True
            result["status"] = "PASS"

            return result

        except Exception as exc:
            result["error_code"] = "CORRUPT_OR_UNREADABLE_FILE"
            result["error_message"] = (
                f"Unable to read PDF document: {type(exc).__name__}"
            )
            return result

        finally:
            if document is not None:
                document.close()

    def _validate_image(
        self,
        path: Path,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate JPG / JPEG / PNG readability.
        """

        try:
            from PIL import Image

            with Image.open(path) as image:
                image.verify()

            # Open again after verify() because verify() invalidates
            # the image object for further operations.
            with Image.open(path) as image:
                width, height = image.size

            if width <= 0 or height <= 0:
                result["error_code"] = "INVALID_IMAGE_DIMENSIONS"
                result["error_message"] = (
                    "The image has invalid dimensions."
                )
                return result

            result["page_count"] = 1
            result["is_readable"] = True
            result["status"] = "PASS"

            return result

        except Exception as exc:
            result["error_code"] = "CORRUPT_OR_UNREADABLE_FILE"
            result["error_message"] = (
                f"Unable to read image: {type(exc).__name__}"
            )
            return result