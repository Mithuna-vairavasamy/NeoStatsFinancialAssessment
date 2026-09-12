from __future__ import annotations

import base64
import json
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from backend.app.schemas.extraction import (
    ExtractionResult,
    InvoiceExtraction,
    BalanceSheetExtraction,
    ProfitLossExtraction,
    CashFlowExtraction,
)


class AIExtractionService:
    """
    AI-based structured document extraction service.

    Gemini is used for multimodal document extraction.

    Supports:
    - JPG
    - JPEG
    - PDF pages rendered as images
    - Native PDF text supplied by extraction service
    - Scanned/image-based PDFs supplied as rendered images

    Responsibilities:
    - Receive OCR/text extraction output.
    - Receive document page images.
    - Extract structured information using Gemini.
    - Preserve meaningful document information.
    - Preserve financial tables and invoice line items.
    - Preserve comparative reporting periods.
    - Preserve evidence and page information where available.
    - Validate AI output using Pydantic.
    - Return application-level ExtractionResult.

    Financial calculations are NOT performed here.
    They are handled separately by the financial validation service.
    """

    REQUEST_TIMEOUT_SECONDS = 120

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.6-flash",
    ):
        if not api_key:
            raise ValueError(
                "Gemini API key is required."
            )

        self.api_key = api_key
        self.model = model

        self.client = genai.Client(
            api_key=self.api_key,
        )

    def build_prompt(
        self,
        document_type: str,
        extraction_result: dict[str, Any],
    ) -> str:
        """
        Build the document extraction prompt.

        The AI returns ONLY the document-specific data object.

        The Python application adds:
        - document_type
        - raw_text
        - pages
        """

        raw_text = extraction_result.get(
            "text",
            "",
        )

        pages = extraction_result.get(
            "pages",
            [],
        )

        pages_for_prompt = []

        for page in pages:
            if not isinstance(page, dict):
                continue

            page_copy = dict(page)

            # Never place base64 image data inside the text prompt.
            # Images are sent separately as Gemini image parts.
            page_copy.pop(
                "image_base64",
                None,
            )

            pages_for_prompt.append(
                page_copy
            )

        return f"""
You are an information extraction system for financial
documents.

The document type has already been selected by the application.

DOCUMENT TYPE:
{document_type}

Do NOT classify the document.

============================================================
SOURCE OCR TEXT
============================================================

{raw_text}

============================================================
SOURCE PAGE INFORMATION
============================================================

{pages_for_prompt}

The page information may contain OCR word-level information:

- text
- confidence
- x
- y
- width
- height

Use coordinates to understand the visual layout.

Coordinates are especially important for financial tables,
invoice rows, and comparative-period columns.

The document page images are also provided separately.

Use the actual page images to verify:

- visual layout
- table structure
- row relationships
- column relationships
- headers
- values
- dates
- parties
- other visible information

Do NOT rely only on flattened OCR text.

============================================================
CORE EXTRACTION REQUIREMENTS
============================================================

1. Extract ALL meaningful visible information supported by the
   source document.

2. Do NOT restrict extraction to only example fields.

3. Preserve meaningful:

   - header information
   - document information
   - dates
   - parties
   - currencies
   - totals
   - subtotals
   - financial statement line items
   - comparative-period values
   - invoice line items
   - financial tables
   - other meaningful visible information

4. Do NOT invent values.

5. Do NOT infer values.

6. Do NOT guess unclear values.

7. Do NOT calculate a missing source value.

8. If a value is missing or unreadable, return null.

9. Preserve values according to the source.

10. Preserve negative values represented using parentheses
    or brackets as negative numeric values.

11. Do not move values between rows.

12. Do not move values between reporting-period columns.

13. Do not silently replace uncertain OCR values with guesses.

============================================================
TABLE EXTRACTION
============================================================

Financial tables are extremely important.

For every meaningful table:

- preserve row labels
- preserve column labels
- preserve visible values
- preserve row/value relationships
- preserve column/value relationships
- preserve reporting-period relationships
- preserve additional visible columns
- do not merge separate rows
- do not drop meaningful rows

When OCR coordinates are available:

- use x positions to identify columns
- use y positions to identify rows
- use nearby words to reconstruct rows
- use visible headings to identify columns
- use visible headings to identify reporting periods

Use the actual page image to verify table structure whenever
OCR ordering is ambiguous.

Do not rely only on flattened OCR text order.

============================================================
COMPARATIVE FINANCIAL PERIODS
============================================================

Financial statements may contain comparative periods.

For example:

31-Mar-17    31-Mar-16

Values belonging to 31-Mar-17 must remain under 31-Mar-17.

Values belonging to 31-Mar-16 must remain under 31-Mar-16.

NEVER swap comparative-period values.

Use the exact visible reporting-period labels whenever
possible.

Do not create a reporting period that is not visible.

============================================================
INVOICE
============================================================

For an invoice preserve:

- invoice number
- invoice date
- vendor name
- customer name
- currency
- subtotal
- tax amount
- discount
- round off
- total amount
- every visible line item
- additional meaningful invoice fields
- additional meaningful tables

For every line item preserve:

- description
- quantity
- unit price
- line total
- additional visible fields such as HSN/SAC
- page number where available

If a numeric value cannot be reliably read:

return null.

Do not put OCR garbage into numeric fields.

============================================================
IMPORTANT INVOICE OUTPUT FORMAT
============================================================

For invoice line_items, follow the InvoiceLineItem schema
exactly.

Each line item must use:

- description: plain string or null
- quantity: plain number or null
- unit_price: plain number or null
- line_total: plain number or null
- extra_fields: object/dictionary containing additional
  visible fields
- page_number: integer or null

Do NOT wrap description, quantity, unit_price, or line_total
inside objects containing "value", "confidence", or "evidence".

Correct format:

{{
  "description": "Replace HVAC Unit.",
  "quantity": 1,
  "unit_price": 2650.00,
  "line_total": 2650.00,
  "extra_fields": {{}},
  "page_number": 1
}}

For additional_fields, return an object/dictionary.

Correct format:

{{
  "additional_fields": {{
    "Due Date": {{
      "value": "01/29/2020",
      "confidence": null,
      "evidence": {{
        "source_text": "01/29/2020",
        "page_number": 1
      }}
    }}
  }}
}}

Do NOT return additional_fields as a list.

For discount and round_off, use the ExtractedField structure.

If the source does not contain the value, return:

{{
  "value": null,
  "confidence": null,
  "evidence": null
}}

Do NOT return discount or round_off as plain null.

============================================================
BALANCE SHEET
============================================================

Preserve:

- statement title
- statement date
- currency
- every reporting period
- every visible liability line
- every visible asset line
- capital
- reserves and surplus
- minority interest
- deposits
- borrowings
- other liabilities and provisions
- total capital and liabilities
- assets
- total assets
- contingent liabilities
- bills for collection
- all other meaningful visible information

Do not create an equity value if it is not explicitly present.

============================================================
IMPORTANT BALANCE SHEET OUTPUT FORMAT
============================================================

For Balance Sheet documents, the "periods" field is the
PRIMARY structured representation of the financial statement.

You MUST populate "periods" whenever reporting-period columns
are visible in the document.

For each visible reporting period, create exactly one period
object:

{{
  "label": "EXACT VISIBLE REPORTING PERIOD",
  "values": {{
    "ROW_NAME": VALUE
  }}
}}

Preserve every meaningful visible financial row inside the
corresponding period's "values" dictionary.

The row names must identify what each number represents.

Do NOT return unlabeled numbers.

Do NOT put the Balance Sheet financial values only inside
"line_items" when comparative reporting periods are visible.

For example, if the document contains rows such as:

Capital
Reserves and surplus
Minority interest
Deposits
Borrowings
Other liabilities and provisions
Total Capital and Liabilities
Cash and balances with RBI
Balances with banks and money at call/short notice
Investments
Advances
Fixed assets
Other assets
Total Assets

the corresponding period should preserve them using clear
machine-readable keys such as:

{{
  "label": "March 31, 2022",
  "values": {{
    "capital": <source value>,
    "reserves_and_surplus": <source value>,
    "minority_interest": <source value>,
    "deposits": <source value>,
    "borrowings": <source value>,
    "other_liabilities_and_provisions": <source value>,
    "total_capital_and_liabilities": <source value>,
    "cash_and_balances_with_rbi": <source value>,
    "balances_with_banks_and_money_at_call_short_notice": <source value>,
    "investments": <source value>,
    "advances": <source value>,
    "fixed_assets": <source value>,
    "other_assets": <source value>,
    "total_assets": <source value>
  }}
}}

The example above describes the REQUIRED STRUCTURE only.

DO NOT copy the example values.

Use the actual values visible in the document.

If a row exists in the source but cannot be reliably read,
include the row key with null.

Do NOT invent missing values.

For every comparative period:

- preserve the exact visible period label
- preserve the correct value for that period
- never swap values between columns
- independently preserve each period

The key:

"total_capital_and_liabilities"

MUST contain the reported Total Capital & Liabilities value
for that period when visible.

The key:

"total_assets"

MUST contain the reported Total Assets value for that period
when visible.

These values are required for deterministic financial
validation.

If the document has multiple reporting periods, create one
period object for EACH visible period.

Do not leave "periods" empty when comparative period columns
are visible.

The "line_items" field may additionally preserve table rows,
but it MUST NOT replace the required "periods" representation.

For Balance Sheet:

- periods = structured comparative financial data
- line_items = additional structured table rows when useful
- additional_fields = other meaningful visible document fields
- additional_tables = additional meaningful tables

Do not move reporting-period values into unrelated fields.

============================================================
PROFIT AND LOSS
============================================================

Preserve:

- statement title
- statement date
- currency
- every reporting period
- interest earned
- other income
- total income
- interest expended
- operating expenses
- provisions and contingencies
- total expenditure
- net profit
- minority interest
- consolidated profit attributable to group
- share in profits of associates
- appropriations
- earnings per share
- every other meaningful visible line item

For comparative Profit & Loss statements, preserve each
reporting period independently inside "periods".

Use meaningful machine-readable row keys.

For example:

{{
  "label": "March 31, 2022",
  "values": {{
    "interest_earned": <source value>,
    "other_income": <source value>,
    "total_income": <source value>,
    "interest_expended": <source value>,
    "operating_expenses": <source value>,
    "provisions_and_contingencies": <source value>,
    "total_expenditure": <source value>,
    "net_profit_before_minority_interest": <source value>,
    "minority_interest": <source value>,
    "share_in_profits_of_associates": <source value>,
    "consolidated_net_profit_attributable_to_group": <source value>
  }}
}}

Use actual source values only.

============================================================
CASH FLOW
============================================================

Preserve:

- statement title
- statement date
- currency
- every reporting period
- operating cash flow items
- investing cash flow items
- financing cash flow items
- foreign exchange / translation adjustment
- net increase or decrease in cash
- opening cash
- closing cash
- every other meaningful visible line item

For comparative Cash Flow statements, preserve each
reporting period independently inside "periods".

Use meaningful machine-readable row keys.

Parentheses and brackets represent negative values.

============================================================
EVIDENCE
============================================================

Where evidence is available:

- preserve the exact relevant source text
- include the source page number
- do not invent evidence

Evidence structure:

{{
    "source_text": "exact relevant source text",
    "page_number": 1
}}

If reliable evidence is unavailable, use null.

============================================================
CONFIDENCE
============================================================

When reliable confidence information is available, provide a
value between 0 and 100.

Do not invent confidence values.

============================================================
MISSING VALUES
============================================================

If a source value is:

- missing
- unreadable
- corrupted
- not reliably extractable

return null.

Do NOT:

- estimate it
- calculate it
- copy it from another period
- copy it from another row
- assume zero
- infer it

============================================================
OUTPUT CONTRACT
============================================================

Return ONLY the JSON object required by the selected
document-specific Pydantic schema.

Do NOT return:

- document_type
- raw_text
- pages
- explanations
- comments
- Markdown
- code fences

The Python application adds document_type, raw_text and pages
after validating the extraction.

For invoice, return exactly these fields:

- invoice_number
- invoice_date
- vendor_name
- customer_name
- currency
- subtotal
- tax_amount
- discount
- round_off
- total_amount
- line_items
- additional_fields
- additional_tables

For balance sheet, return:

- statement_title
- statement_date
- currency
- periods
- line_items
- additional_fields
- additional_tables

For profit and loss, return:

- statement_title
- statement_date
- currency
- periods
- line_items
- additional_fields
- additional_tables

For cash flow, return:

- statement_title
- statement_date
- currency
- periods
- line_items
- additional_fields
- additional_tables

Missing values must be null.

============================================================
FINAL ACCURACY CHECK
============================================================

Before returning JSON:

1. Consider all meaningful visible information.

2. Consider every meaningful financial statement row.

3. Preserve comparative periods correctly.

4. Do not swap columns.

5. Consider every visible invoice line item.

6. Use null for missing or unreliable values.

7. Do not invent values.

8. Preserve negative values.

9. Preserve evidence where available.

10. For Balance Sheet, ensure every visible reporting period
    is represented inside "periods".

11. For Balance Sheet, ensure Total Assets and Total Capital
    & Liabilities are mapped to their correct period.

12. For Profit & Loss, preserve every comparative period
    independently.

13. For Cash Flow, preserve every comparative period
    independently.

14. Return only the required JSON object.

DOCUMENT TYPE:
{document_type}
"""


    def _get_schema_model(
        self,
        document_type: str,
    ):
        schema_models = {
            "invoice": InvoiceExtraction,
            "balance_sheet": BalanceSheetExtraction,
            "profit_and_loss": ProfitLossExtraction,
            "cash_flow": CashFlowExtraction,
            "cash_flow_statement": CashFlowExtraction,
        }

        schema_model = schema_models.get(
            document_type
        )

        if schema_model is None:
            raise ValueError(
                f"Unsupported document type: {document_type}"
            )

        return schema_model


    @staticmethod
    def _build_contents(
        prompt: str,
        extraction_result: dict[str, Any],
    ) -> list[Any]:
        """
        Build Gemini multimodal contents.

        Text is sent as a normal text part.

        Every page image is decoded from base64 and sent as an
        inline JPEG image part.

        This supports:
        - JPG
        - JPEG
        - scanned PDFs
        - native PDFs rendered to page images
        """

        contents: list[Any] = [
            prompt
        ]

        pages = extraction_result.get(
            "pages",
            [],
        )

        image_count = 0

        for page in pages:

            if not isinstance(page, dict):
                continue

            image_base64 = page.get(
                "image_base64"
            )

            if not image_base64:
                continue

            try:
                image_bytes = base64.b64decode(
                    image_base64
                )
            except Exception as exc:
                raise ValueError(
                    "Invalid base64 image data "
                    f"for page {page.get('page_number')}: {exc}"
                ) from exc

            contents.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg",
                )
            )

            image_count += 1

        if image_count == 0:
            raise ValueError(
                "No document page images were available "
                "for Gemini extraction."
            )

        return contents


    @staticmethod
    def _get_response_text(
        response: Any,
    ) -> str:
        """
        Safely extract Gemini response text.
        """

        text = getattr(
            response,
            "text",
            None,
        )

        if isinstance(text, str):
            return text.strip()

        return ""


    @staticmethod
    def _parse_json_response(
        response_text: str,
    ) -> dict[str, Any]:
        """
        Parse Gemini response as JSON.

        Small tolerance is allowed for accidental Markdown
        code fences.

        No values are modified.
        """

        text = response_text.strip()

        if not text:
            raise ValueError(
                "Gemini returned an empty response."
            )

        if text.lower() in {
            "none",
            "null",
            "undefined",
        }:
            raise ValueError(
                "Gemini returned unusable empty content."
            )

        if text.startswith("```"):

            lines = text.splitlines()

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            text = "\n".join(
                lines
            ).strip()

        try:
            parsed = json.loads(
                text
            )

        except json.JSONDecodeError as exc:

            raise ValueError(
                "Gemini returned invalid JSON: "
                f"{exc}"
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                "Gemini JSON response must be an object."
            )

        return parsed


    def extract(
        self,
        document_type: str,
        extraction_result: dict[str, Any],
    ) -> ExtractionResult:
        """
        Perform Gemini multimodal extraction.

        Success requires:

        1. Gemini request succeeds.
        2. Response contains content.
        3. Content is valid JSON.
        4. JSON is an object.
        5. JSON passes the selected Pydantic schema.
        6. Final ExtractionResult passes Pydantic validation.
        """

        prompt = self.build_prompt(
            document_type=document_type,
            extraction_result=extraction_result,
        )

        schema_model = self._get_schema_model(
            document_type
        )

        contents = self._build_contents(
            prompt=prompt,
            extraction_result=extraction_result,
        )

        print(
            "\n===================================================="
        )

        print(
            "GEMINI EXTRACTION ATTEMPT"
        )

        print(
            f"Model: {self.model}"
        )

        print(
            f"Document type: {document_type}"
        )

        print(
            "Multimodal images: "
            f"{sum(1 for page in extraction_result.get('pages', []) if isinstance(page, dict) and page.get('image_base64'))}"
        )

        print(
            "====================================================\n"
        )

        try:

            response = (
                self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0,
                        response_mime_type="application/json",
                    ),
                )
            )

        except Exception as exc:

            print(
                "\n================ GEMINI REQUEST ERROR ================\n"
            )

            print(
                f"Model: {self.model}"
            )

            print(
                repr(exc)
            )

            print(
                "\n=======================================================\n"
            )

            raise RuntimeError(
                "Gemini extraction request failed: "
                f"{exc}"
            ) from exc

        print(
            "\n================ GEMINI RESPONSE ====================="
        )

        print(
            f"Model requested: {self.model}"
        )

        print(
            "=======================================================\n"
        )

        response_text = self._get_response_text(
            response
        )

        if not response_text:

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        print(
            "\n================ GEMINI RAW RESPONSE ================\n"
        )

        print(
            response_text
        )

        print(
            "\n=======================================================\n"
        )

        # =====================================================
        # JSON PARSING
        # =====================================================

        try:

            parsed_json = (
                self._parse_json_response(
                    response_text
                )
            )

        except ValueError as exc:

            print(
                "\n================ INVALID GEMINI JSON ================\n"
            )

            print(
                exc
            )

            print(
                "\n=======================================================\n"
            )

            raise RuntimeError(
                f"Gemini extraction returned invalid JSON: {exc}"
            ) from exc


        try:

            extracted_document = (
                schema_model.model_validate(
                    parsed_json
                )
            )

        except ValidationError as exc:

            print(
                "\n================ GEMINI VALIDATION ERROR =============\n"
            )

            print(
                exc
            )

            print(
                "\n================ RAW JSON =============================\n"
            )

            print(
                json.dumps(
                    parsed_json,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            print(
                "\n=======================================================\n"
            )

            raise RuntimeError(
                "Gemini response failed Pydantic validation."
            ) from exc


        final_result = ExtractionResult(
            document_type=document_type,
            data=extracted_document,
            raw_text=extraction_result.get(
                "text",
                "",
            ),
            pages=extraction_result.get(
                "pages",
                [],
            ),
        )


        try:

            validated_result = (
                ExtractionResult.model_validate(
                    final_result.model_dump()
                )
            )

        except ValidationError as exc:

            print(
                "\n=========== FINAL EXTRACTION VALIDATION ERROR ========\n"
            )

            print(
                exc
            )

            print(
                "\n=======================================================\n"
            )

            raise RuntimeError(
                "Final extraction result failed Pydantic validation."
            ) from exc


        print(
            "\n===================================================="
        )

        print(
            "GEMINI EXTRACTION SUCCESS"
        )

        print(
            f"Model used: {self.model}"
        )

        print(
            f"Document type: {document_type}"
        )

        print(
            "====================================================\n"
        )

        return validated_result