from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_documents():
    response = client.get("/api/v1/documents/")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_document_not_found():
    response = client.get(
        "/api/v1/documents/nonexistent-document.pdf"
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"]["code"] == "DOCUMENT_NOT_FOUND"


def test_invalid_document_type():
    response = client.post(
        "/api/v1/documents/process",
        data={
            "document_type": "unsupported_type"
        },
        files={
            "file": (
                "test.pdf",
                b"test document",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400

    data = response.json()

    assert data["detail"]["code"] == "INVALID_DOCUMENT_TYPE"


def test_unsupported_file_type():
    response = client.post(
        "/api/v1/documents/process",
        data={
            "document_type": "invoice"
        },
        files={
            "file": (
                "test.txt",
                b"invalid document",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400

    data = response.json()

    assert data["detail"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_empty_file():
    response = client.post(
        "/api/v1/documents/process",
        data={
            "document_type": "invoice"
        },
        files={
            "file": (
                "empty.pdf",
                b"",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400

    data = response.json()

    assert data["detail"]["code"] == "EMPTY_FILE"