from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.repositories.document_repository import (
    DocumentRepository,
)
from backend.app.services.document_validation_service import (
    DocumentValidationService,
)
from backend.app.services.extraction_service import ExtractionService
from backend.app.services.ai_extraction_service import AIExtractionService
from backend.app.services.financial_validation_service import (
    FinancialValidationService,
)


class DocumentService:
    """
    Coordinates the complete document-processing pipeline.

    Pipeline:
    1. Validate document
    2. Extract text / OCR
    3. AI-based structured extraction
    4. Financial calculation validation
    5. Build the final company-required JSON response
    6. Store processing result
    """

    def __init__(
    self,
    db: Session,
    gemini_api_key: str,
    gemini_model: str = "gemini-3.6-flash",
    financial_tolerance: float = 0.01,
):
        self.document_repository = DocumentRepository(db)

        self.document_validation_service = (
            DocumentValidationService()
        )

        self.extraction_service = ExtractionService()

        self.ai_extraction_service = AIExtractionService(
            api_key=gemini_api_key,
            model=gemini_model,
        )

        self.financial_validation_service = (
            FinancialValidationService(
                tolerance=financial_tolerance
            )
        )

    def process_document(
        self,
        file_path: str,
        document_type: str,
        document_name: str | None = None,
    ) -> dict[str, Any]:

        start_time = time.perf_counter()

        if document_name is None:
            document_name = (
                file_path.split("\\")[-1].split("/")[-1]
            )


        validation_result = (
            self.document_validation_service.validate(
                file_path
            )
        )

        if validation_result["status"] != "PASS":
            processing_time_ms = int(
                (time.perf_counter() - start_time) * 1000
            )

            response = {
                "document_name": document_name,
                "document_type": document_type,
                "processing_status": "FAILED",
                "overall_confidence": None,
                "file_validation": {
                    "file_type": validation_result.get(
                        "file_type",
                        "",
                    ),
                    "is_supported": validation_result.get(
                        "is_supported",
                        False,
                    ),
                    "is_readable": validation_result.get(
                        "is_readable",
                        False,
                    ),
                    "page_count": validation_result.get(
                        "page_count",
                        0,
                    ),
                    "status": validation_result.get(
                        "status",
                        "FAILED",
                    ),
                },
                "extracted_data": None,
                "validation": {
                    "checks": [],
                    "overall_status": "NOT_APPLICABLE",
                    "issues": [],
                },
                "processing_metadata": {
                    "ocr_used": False,
                    "processed_at": self._processed_at(),
                    "processing_time_ms": processing_time_ms,
                },
            }

            self.document_repository.create(
                document_name=document_name,
                document_type=document_type,
                processing_status=response["processing_status"],
                result=response,
            )

            return response

        extraction_result = (
            self.extraction_service.extract(
                file_path
            )
        )

        ai_result = self.ai_extraction_service.extract(
            document_type=document_type,
            extraction_result=extraction_result,
        )

        extracted_data = ai_result.data

        financial_validation = (
            self._validate_financial_data(
                document_type=document_type,
                extracted_data=extracted_data,
            )
        )


        processing_time_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        ocr_confidence = extraction_result.get(
            "confidence"
        )

        overall_confidence = (
            ocr_confidence / 100
            if ocr_confidence is not None
            else None
        )

        response = {
            "document_name": document_name,
            "document_type": document_type,
            "processing_status": self._processing_status(
                financial_validation
            ),
            "overall_confidence": overall_confidence,
            "file_validation": {
                "file_type": validation_result.get(
                    "file_type",
                    "",
                ),
                "is_supported": validation_result.get(
                    "is_supported",
                    False,
                ),
                "is_readable": validation_result.get(
                    "is_readable",
                    False,
                ),
                "page_count": validation_result.get(
                    "page_count",
                    0,
                ),
                "status": validation_result.get(
                    "status",
                    "FAILED",
                ),
            },
            "extracted_data": extracted_data.model_dump(),
            "validation": financial_validation,
            "processing_metadata": {
                "ocr_used": extraction_result.get(
                    "ocr_used",
                    False,
                ),
                "processed_at": self._processed_at(),
                "processing_time_ms": processing_time_ms,
            },
        }

        self.document_repository.create(
            document_name=document_name,
            document_type=document_type,
            processing_status=response["processing_status"],
            result=response,
        )

        return response


    def _validate_financial_data(
        self,
        document_type: str,
        extracted_data: Any,
    ) -> dict[str, Any]:

        if document_type == "invoice":
            return self._validate_invoice(
                extracted_data
            )

        if document_type == "balance_sheet":
            return self._validate_balance_sheet(
                extracted_data
            )

        if document_type == "profit_and_loss":
            return self._validate_profit_and_loss(
                extracted_data
            )

        if document_type in {
            "cash_flow",
            "cash_flow_statement",
        }:
            return self._validate_cash_flow(
                extracted_data
            )

        return {
            "checks": [],
            "overall_status": "NOT_APPLICABLE",
            "issues": [],
        }


    def _validate_invoice(
        self,
        extracted_data: Any,
    ) -> dict[str, Any]:

        line_items = [
            item.model_dump()
            for item in extracted_data.line_items
        ]

        return (
            self.financial_validation_service.validate_invoice(
                line_items=line_items,
                subtotal=self._field_value(
                    extracted_data,
                    "subtotal",
                ),
                tax_amount=self._field_value(
                    extracted_data,
                    "tax_amount",
                ),
                discount=self._field_value(
                    extracted_data,
                    "discount",
                ),
                round_off=self._field_value(
    extracted_data,
    "round_off",
),
                total_amount=self._field_value(
                    extracted_data,
                    "total_amount",
                ),
                cash_paid=self._field_value(
                    extracted_data,
                    "cash_paid",
                ),
                change=self._field_value(
                    extracted_data,
                    "change",
                ),
            )
        )


    def _validate_balance_sheet(
        self,
        extracted_data: Any,
    ) -> dict[str, Any]:

        periods = [
            period.model_dump()
            for period in extracted_data.periods
        ]

        return (
            self.financial_validation_service
            .validate_balance_sheet(
                periods=periods
            )
        )


    def _validate_profit_and_loss(
        self,
        extracted_data: Any,
    ) -> dict[str, Any]:

        periods = [
            period.model_dump()
            for period in extracted_data.periods
        ]

        return (
            self.financial_validation_service
            .validate_profit_and_loss(
                periods=periods
            )
        )

    def _validate_cash_flow(
        self,
        extracted_data: Any,
    ) -> dict[str, Any]:

        periods = [
            period.model_dump()
            for period in extracted_data.periods
        ]

        return (
            self.financial_validation_service
            .validate_cash_flow(
                periods=periods
            )
        )


    def _field_value(
        self,
        extracted_data: Any,
        field_name: str,
    ) -> Any:

        field = getattr(
            extracted_data,
            field_name,
            None,
        )

        if field is None:
            return None

        return getattr(
            field,
            "value",
            None,
        )

    def _processed_at(self) -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    def _processing_status(
        self,
        financial_validation: dict[str, Any],
    ) -> str:

        validation_status = (
            financial_validation.get(
                "overall_status"
            )
        )

        if validation_status == "FAIL":
            return "FAILED"

        if validation_status == "NOT_APPLICABLE":
            return "NOT_APPLICABLE"

        return "PASS"