from pathlib import Path
from tempfile import NamedTemporaryFile
import json

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.repositories.document_repository import (
    DocumentRepository,
)
from backend.app.schemas.document import DocumentResponse
from backend.app.services.document_service import DocumentService


router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
)


@router.post(
    "/process",
    response_model=DocumentResponse,
)
async def process_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: Session = Depends(get_db),
):
    allowed_document_types = {
        "invoice",
        "balance_sheet",
        "profit_and_loss",
        "cash_flow_statement",
    }

    if document_type not in allowed_document_types:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DOCUMENT_TYPE",
                "message": "Unsupported document type.",
            },
        )

    file_suffix = Path(
        file.filename or ""
    ).suffix.lower()

    if file_suffix not in {
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
    }:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": (
                    "Only PDF / JPG / PNG documents are supported."
                ),
            },
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "EMPTY_FILE",
                "message": "The uploaded file is empty.",
            },
        )

    temporary_path = None

    try:
        with NamedTemporaryFile(
            delete=False,
            suffix=file_suffix,
        ) as temporary_file:
            temporary_file.write(file_bytes)
            temporary_path = temporary_file.name

        service = DocumentService(
    db=db,
    gemini_api_key=settings.gemini_api_key,
    gemini_model=settings.gemini_model,
    financial_tolerance=settings.financial_tolerance,
)

        result = service.process_document(
            file_path=temporary_path,
            document_type=document_type,
            document_name=file.filename,
        )

        return result

    except HTTPException:
        raise

    except Exception as exc:
        error_text = str(exc)

        print(
            f"Document processing error: "
            f"{type(exc).__name__}: {error_text}"
        )

        if "quota" in error_text.lower():
            raise HTTPException(
        status_code=503,
        detail={
            "code": "AI_QUOTA_EXCEEDED",
            "message": (
                "AI extraction is temporarily unavailable "
                "because the AI provider quota has been exceeded. "
                "Please try again later."
            ),
        },
    )

        if (
            "503" in error_text
            or "UNAVAILABLE" in error_text
            or "high demand" in error_text.lower()
        ):
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "AI_SERVICE_UNAVAILABLE",
                    "message": (
                        "AI extraction is temporarily unavailable. "
                        "Please try again later."
                    ),
                },
            )


        raise HTTPException(
            status_code=502,
            detail={
                "code": "DOCUMENT_PROCESSING_FAILED",
                "message": (
                    "Document processing failed. "
                    "Please check the backend logs for details."
                ),
            },
        )

    finally:
        if temporary_path:
            Path(temporary_path).unlink(
                missing_ok=True
            )


@router.get(
    "/{document_name}",
    response_model=DocumentResponse,
)
def get_document(
    document_name: str,
    db: Session = Depends(get_db),
):
    repository = DocumentRepository(db)

    document = repository.get_by_name(
        document_name
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": "Document not found.",
            },
        )

    return json.loads(document.result_json)


@router.get("/")
def list_documents(
    db: Session = Depends(get_db),
):
    repository = DocumentRepository(db)

    documents = repository.get_all()

    return [
        {
            "document_name": document.document_name,
            "document_type": document.document_type,
            "processing_status": document.processing_status,
            "created_at": document.created_at.isoformat(),
        }
        for document in documents
    ]