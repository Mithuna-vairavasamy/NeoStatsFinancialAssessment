from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes.documents import router as documents_router
from backend.app.core.database import create_tables


BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"


app = FastAPI(
    title="NeoStats Document Intelligence API",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    create_tables()


app.mount(
    "/static",
    StaticFiles(
        directory=FRONTEND_DIR / "static"
    ),
    name="static",
)


@app.get("/")
def dashboard():
    return FileResponse(
        FRONTEND_DIR / "templates" / "dashboard.html"
    )
@app.get("/documents/{document_name}")
def document_result_page(document_name: str):
    return FileResponse(
        FRONTEND_DIR / "templates" / "document_result.html"
    )

app.include_router(documents_router)


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}