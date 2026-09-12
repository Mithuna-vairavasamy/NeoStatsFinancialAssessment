from __future__ import annotations

import base64
from pathlib import Path
from typing import Any
import os
import cv2
import numpy as np
import pymupdf
import pytesseract


class ExtractionService:
    """
    Extract text from PDF and image documents.

    PDF strategy:
    - Use native PDF text when clearly available.
    - If native text is weak, render the page at a controlled
      resolution and use Tesseract OCR.
    - Preserve a compressed page image for Gemini.

    Image strategy:
    - Read JPG/JPEG/PNG using OpenCV.
    - Use Tesseract OCR.
    - Preserve a compressed page image for Gemini.
    """

    PDF_OCR_DPI = 200

    GEMINI_MAX_DIMENSION = 1800

    GEMINI_JPEG_QUALITY = 70

    def __init__(
            self,
            tesseract_path: str | None = None,
        ):
            if tesseract_path:
                self.tesseract_path = tesseract_path
            elif os.name == "nt":
                self.tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            else:
                self.tesseract_path = "/opt/render/project/src/.render/tesseract/bin/tesseract"
    
            if not Path(self.tesseract_path).exists():
                raise FileNotFoundError(
                    f"Tesseract executable not found: "
                    f"{self.tesseract_path}"
                )
    
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path


    def preprocess_image(
        self,
        image: np.ndarray,
    ) -> np.ndarray:
        """
        Keep the document image unchanged.

        OCR and Gemini image compression are handled separately.
        """

        if image is None:
            raise ValueError(
                "Unable to read image."
            )

        return image


    def ocr_image(
        self,
        image: np.ndarray,
    ) -> dict[str, Any]:

        processed = self.preprocess_image(
            image
        )

        config = "--oem 3 --psm 4"

        text = pytesseract.image_to_string(
            processed,
            lang="eng",
            config=config,
        )

        data = pytesseract.image_to_data(
            processed,
            lang="eng",
            config=config,
            output_type=pytesseract.Output.DICT,
        )

        confidences = []
        words = []

        for i, confidence in enumerate(
            data["conf"]
        ):
            try:
                value = float(
                    confidence
                )

                if value >= 0:
                    confidences.append(
                        value
                    )

                    word = data[
                        "text"
                    ][i].strip()

                    if word:
                        words.append(
                            {
                                "text": word,
                                "confidence": value,
                                "x": data["left"][i],
                                "y": data["top"][i],
                                "width": data["width"][i],
                                "height": data["height"][i],
                            }
                        )

            except (
                ValueError,
                TypeError,
            ):
                continue

        average_confidence = (
            sum(confidences)
            / len(confidences)
            if confidences
            else 0.0
        )

        return {
            "text": text.strip(),
            "confidence": round(
                average_confidence,
                2,
            ),
            "method": "tesseract_ocr",
            "words": words,
        }


    def render_pdf_page(
        self,
        page,
    ) -> np.ndarray:
        """
        Render one PDF page at a controlled resolution.

        200 DPI is used instead of 300 DPI to avoid very large
        in-memory PNG images that can cause Tesseract/Leptonica
        memory allocation failures.
        """

        scale = (
            self.PDF_OCR_DPI / 72
        )

        matrix = pymupdf.Matrix(
            scale,
            scale,
        )

        pixmap = page.get_pixmap(
            matrix=matrix,
            alpha=False,
        )

        image_bytes = pixmap.tobytes(
            "jpg",
            jpg_quality=85,
        )

        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8,
        )

        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR,
        )

        if image is None:
            raise ValueError(
                "Unable to decode rendered PDF page."
            )

        return image

    @staticmethod
    def encode_image(
        image: np.ndarray,
    ) -> str:
        """
        Create a compressed JPEG image for Gemini.

        The original image is used for OCR.

        Only the Gemini copy is resized/compressed.
        """

        if image is None:
            raise ValueError(
                "Unable to encode empty image."
            )

        max_dimension = (
            ExtractionService.GEMINI_MAX_DIMENSION
        )

        height, width = image.shape[:2]

        if max(height, width) > max_dimension:

            scale = (
                max_dimension
                / max(height, width)
            )

            new_width = max(
                1,
                int(width * scale),
            )

            new_height = max(
                1,
                int(height * scale),
            )

            image = cv2.resize(
                image,
                (
                    new_width,
                    new_height,
                ),
                interpolation=cv2.INTER_AREA,
            )

        success, buffer = cv2.imencode(
            ".jpg",
            image,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                ExtractionService.GEMINI_JPEG_QUALITY,
            ],
        )

        if not success:
            raise ValueError(
                "Unable to encode page image."
            )

        return base64.b64encode(
            buffer.tobytes()
        ).decode("utf-8")

    def extract_pdf(
        self,
        file_path: str,
    ) -> dict[str, Any]:

        document = pymupdf.open(
            file_path
        )

        pages = []
        all_text = []

        ocr_used = False
        confidences = []

        native_page_count = 0
        ocr_page_count = 0

        try:

            for page_index in range(
                len(document)
            ):

                page = document[
                    page_index
                ]

                page_number = (
                    page_index + 1
                )


                native_text = (
                    page.get_text(
                        "text"
                    ).strip()
                )

                use_native = (
                    len(native_text) >= 200
                )


                if use_native:

                    page_text = (
                        native_text
                    )

                    page_confidence = None
                    method = "native_pdf"
                    page_words = []

                    image = (
                        self.render_pdf_page(
                            page
                        )
                    )

                    page_image_base64 = (
                        self.encode_image(
                            image
                        )
                    )

                    native_page_count += 1

                else:

                    image = (
                        self.render_pdf_page(
                            page
                        )
                    )

                    page_image_base64 = (
                        self.encode_image(
                            image
                        )
                    )

                    ocr_result = (
                        self.ocr_image(
                            image
                        )
                    )

                    page_text = (
                        ocr_result[
                            "text"
                        ]
                    )

                    page_confidence = (
                        ocr_result[
                            "confidence"
                        ]
                    )

                    method = (
                        "tesseract_ocr"
                    )

                    page_words = (
                        ocr_result.get(
                            "words",
                            [],
                        )
                    )

                    ocr_used = True
                    ocr_page_count += 1

                    confidences.append(
                        page_confidence
                    )

                pages.append(
                    {
                        "page_number": (
                            page_number
                        ),
                        "text": page_text,
                        "confidence": (
                            page_confidence
                        ),
                        "method": method,
                        "words": page_words,
                        "image_base64": (
                            page_image_base64
                        ),
                    }
                )

                all_text.append(
                    f"--- Page {page_number} ---\n"
                    f"{page_text}"
                )

        finally:
            document.close()

        confidence = (
            round(
                sum(confidences)
                / len(confidences),
                2,
            )
            if confidences
            else None
        )


        if (
            native_page_count > 0
            and ocr_page_count > 0
        ):

            extraction_method = (
                "mixed_native_pdf_and_ocr"
            )

        elif ocr_page_count > 0:

            extraction_method = (
                "tesseract_ocr"
            )

        else:

            extraction_method = (
                "native_pdf"
            )

        return {
            "text": "\n\n".join(
                all_text
            ),
            "pages": pages,
            "extraction_method": (
                extraction_method
            ),
            "ocr_used": ocr_used,
            "confidence": confidence,
        }


    def extract_image(
        self,
        file_path: str,
    ) -> dict[str, Any]:

        image = cv2.imread(
            file_path,
            cv2.IMREAD_COLOR,
        )

        if image is None:
            raise ValueError(
                f"Unable to read image: "
                f"{file_path}"
            )

        ocr_result = (
            self.ocr_image(
                image
            )
        )

        page_image_base64 = (
            self.encode_image(
                image
            )
        )

        return {
            "text": ocr_result[
                "text"
            ],
            "pages": [
                {
                    "page_number": 1,
                    "text": ocr_result[
                        "text"
                    ],
                    "confidence": (
                        ocr_result[
                            "confidence"
                        ]
                    ),
                    "method": (
                        "tesseract_ocr"
                    ),
                    "words": (
                        ocr_result.get(
                            "words",
                            [],
                        )
                    ),
                    "image_base64": (
                        page_image_base64
                    ),
                }
            ],
            "extraction_method": (
                "tesseract_ocr"
            ),
            "ocr_used": True,
            "confidence": (
                ocr_result[
                    "confidence"
                ]
            ),
        }


    def extract(
        self,
        file_path: str,
    ) -> dict[str, Any]:

        path = Path(
            file_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: "
                f"{file_path}"
            )

        extension = (
            path.suffix.lower()
        )

        # PDF
        if extension == ".pdf":

            return self.extract_pdf(
                str(path)
            )

        if extension in {
            ".jpg",
            ".jpeg",
            ".png",
        }:

            return self.extract_image(
                str(path)
            )

        raise ValueError(
            f"Unsupported file type: "
            f"{extension}"
        )