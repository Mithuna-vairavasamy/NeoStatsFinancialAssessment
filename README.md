# NeoStats Document Intelligence

AI Engineer Internship Technical Case Study – Document Intelligence

## Overview

This project implements a document intelligence pipeline for processing financial documents.

The system supports:

- Invoice
- Balance Sheet
- Profit & Loss
- Cash Flow

The processing flow is:

Document Upload  
→ Document Validation  
→ Text Extraction / OCR  
→ AI-based Field & Table Extraction  
→ Structured JSON Output  
→ Financial Calculation Validation  
→ Confidence / Evidence  
→ Store Processing Result  
→ PASS / FAILED  
→ Dashboard + REST API Response

## Technology Stack

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL

### Document Processing

- PyMuPDF for PDF text extraction and PDF page rendering
- Tesseract OCR for scanned/image-based documents
- OpenCV for image processing

### AI Extraction

- Google Gemini
- Gemini 3.6 Flash
- Structured JSON output validated using Pydantic

### Frontend

- HTML
- CSS
- JavaScript

### Testing

- pytest
- FastAPI TestClient

## Supported Input Formats

The API accepts:

- PDF
- JPG
- JPEG
- PNG

Documents can be:

- Native text PDFs
- Scanned PDFs
- Image-based documents
- JPG/PNG images

The maximum supported document length is 3 pages.

## Supported Document Types

The document type is selected by the user through the frontend and sent to the backend as request metadata.

Supported values:

```text
invoice
balance_sheet
profit_and_loss
cash_flow_statement