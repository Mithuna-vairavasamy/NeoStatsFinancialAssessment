import os
from typing import Any

import cv2
import pytesseract


class OCRService:
    """
    OCR service using Tesseract with OpenCV preprocessing.

    Supports:
    - JPG
    - JPEG
    - PNG

    The service:
    1. Reads the image.
    2. Converts it to grayscale.
    3. Upscales the image.
    4. Applies adaptive thresholding.
    5. Runs Tesseract OCR.
    6. Returns extracted text and confidence.
    """

    def __init__(self, tesseract_path: str | None = None):

        if tesseract_path:
            self.tesseract_path = tesseract_path
        elif os.getenv("TESSERACT_PATH"):
            self.tesseract_path = os.getenv("TESSERACT_PATH")
        elif os.name == "nt":
            self.tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        else:
            self.tesseract_path = "/opt/render/project/src/.render/tesseract/bin/tesseract"

        if not os.path.exists(self.tesseract_path):
            raise FileNotFoundError(
                f"Tesseract executable not found: {self.tesseract_path}"
            )

        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

    def preprocess_image(self, image_path: str):
        """
        Prepare an image for OCR.
        """

        image = cv2.imread(image_path)

        if image is None:
            raise ValueError(
                f"Unable to read image: {image_path}"
            )

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        gray = cv2.resize(
            gray,
            None,
            fx=2,
            fy=2,
            interpolation=cv2.INTER_CUBIC,
        )

        gray = cv2.GaussianBlur(
            gray,
            (3, 3),
            0,
        )

        processed = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )

        return processed

    def extract_text(self, image_path: str) -> dict[str, Any]:
        """
        Run OCR on an image.

        Returns:
            {
                "text": "...",
                "confidence": 0.0,
                "words": [
                    {
                        "text": "...",
                        "confidence": 0.0,
                        "x": 0,
                        "y": 0,
                        "width": 0,
                        "height": 0
                    }
                ],
                "ocr_engine": "tesseract",
                "language": "eng",
                "page_segmentation_mode": 6
            }
        """

        processed_image = self.preprocess_image(image_path)

        config = "--oem 3 --psm 6"

        text = pytesseract.image_to_string(
            processed_image,
            lang="eng",
            config=config,
        )

        data = pytesseract.image_to_data(
            processed_image,
            lang="eng",
            config=config,
            output_type=pytesseract.Output.DICT,
        )

        confidences = []
        words = []

        for i, confidence in enumerate(data["conf"]):

            try:
                value = float(confidence)
            except (ValueError, TypeError):
                continue

            if value < 0:
                continue

            word = data["text"][i].strip()

            if not word:
                continue

            confidences.append(value)

            words.append(
                {
                    "text": word,
                    "confidence": round(value, 2),
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "width": data["width"][i],
                    "height": data["height"][i],
                }
            )

        average_confidence = (
            sum(confidences) / len(confidences)
            if confidences
            else 0.0
        )

        return {
            "text": text.strip(),
            "confidence": round(average_confidence, 2),
            "words": words,
            "ocr_engine": "tesseract",
            "language": "eng",
            "page_segmentation_mode": 6,
        }