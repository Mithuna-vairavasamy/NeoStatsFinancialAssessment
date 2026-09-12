import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.document import Document


class DocumentRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        document_name: str,
        document_type: str,
        processing_status: str,
        result: dict[str, Any],
    ) -> Document:

        document = Document(
            document_name=document_name,
            document_type=document_type,
            processing_status=processing_status,
            result_json=json.dumps(result),
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        return document

    def get_by_name(
    self,
    document_name: str,
) -> Document | None:

        statement = (
        select(Document)
        .where(Document.document_name == document_name)
        .order_by(Document.created_at.desc())
        .limit(1)
    )

        return self.db.execute(statement).scalar_one_or_none()

    def get_all(self) -> list[Document]:

        statement = (
            select(Document)
            .order_by(Document.created_at.desc())
        )

        return list(self.db.execute(statement).scalars().all())