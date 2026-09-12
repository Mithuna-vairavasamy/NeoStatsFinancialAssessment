from typing import Any

from pydantic import BaseModel, Field


class FileValidationResponse(BaseModel):
    file_type: str
    is_supported: bool
    is_readable: bool
    page_count: int
    status: str


class ValidationCheck(BaseModel):
    name: str
    formula: str
    operands: dict[str, Any] = Field(default_factory=dict)
    calculated_value: float | None = None
    reported_value: float | None = None
    variance: float | None = None
    status: str


class ValidationResponse(BaseModel):
    checks: list[ValidationCheck] = Field(default_factory=list)
    overall_status: str
    issues: list[str] = Field(default_factory=list)


class ProcessingMetadata(BaseModel):
    ocr_used: bool
    processed_at: str
    processing_time_ms: int


class DocumentResponse(BaseModel):
    document_name: str
    document_type: str
    processing_status: str
    overall_confidence: float | None = None
    file_validation: FileValidationResponse
    extracted_data: dict[str, Any] | None = None
    validation: ValidationResponse
    processing_metadata: ProcessingMetadata