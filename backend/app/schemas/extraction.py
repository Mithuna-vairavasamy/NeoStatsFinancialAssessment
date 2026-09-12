from typing import Any, Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """
    Source evidence for an extracted value.
    """

    source_text: str | None = None

    page_number: int | None = None


class ExtractedField(BaseModel):
    """
    A single extracted document field.

    Missing or unavailable values must remain None.
    No value should be invented or inferred.
    """

    value: Any = None

    confidence: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    evidence: Evidence | None = None


class TableRow(BaseModel):
    """
    A flexible structured table row.

    The values dictionary preserves meaningful visible
    table columns and their values.
    """

    values: dict[str, Any] = Field(
        default_factory=dict
    )

    page_number: int | None = None


class FinancialStatementPeriod(BaseModel):
    """
    One reporting period from a financial statement.

    Comparative periods are kept independently.
    """

    label: str | None = None

    values: dict[str, Any] = Field(
        default_factory=dict
    )

class InvoiceLineItem(BaseModel):
    """
    Structured invoice line item.

    Required financial fields are represented explicitly.
    Additional visible columns are preserved in extra_fields.
    """

    description: str | None = None

    quantity: float | None = None

    unit_price: float | None = None

    line_total: float | None = None

    extra_fields: dict[str, Any] = Field(
        default_factory=dict
    )

    page_number: int | None = None


class InvoiceExtraction(BaseModel):
    """
    Structured extraction for an Invoice.
    """

    document_type: Literal["invoice"] = "invoice"

    invoice_number: ExtractedField = Field(
        default_factory=ExtractedField
    )

    invoice_date: ExtractedField = Field(
        default_factory=ExtractedField
    )

    vendor_name: ExtractedField = Field(
        default_factory=ExtractedField
    )

    customer_name: ExtractedField = Field(
        default_factory=ExtractedField
    )

    currency: ExtractedField = Field(
        default_factory=ExtractedField
    )

    subtotal: ExtractedField = Field(
        default_factory=ExtractedField
    )

    tax_amount: ExtractedField = Field(
        default_factory=ExtractedField
    )

    discount: ExtractedField = Field(
        default_factory=ExtractedField
    )
    round_off: ExtractedField = Field(
    default_factory=ExtractedField
)
    total_amount: ExtractedField = Field(
        default_factory=ExtractedField
    )

    line_items: list[InvoiceLineItem] = Field(
        default_factory=list
    )

    additional_fields: dict[str, ExtractedField] = Field(
        default_factory=dict
    )

    additional_tables: list[TableRow] = Field(
        default_factory=list
    )


class BalanceSheetExtraction(BaseModel):
    """
    Structured extraction for a Balance Sheet.

    Comparative reporting periods are preserved separately.
    All meaningful visible financial line items can be stored
    inside each period's values dictionary.
    """

    document_type: Literal["balance_sheet"] = (
        "balance_sheet"
    )

    statement_title: ExtractedField = Field(
        default_factory=ExtractedField
    )

    statement_date: ExtractedField = Field(
        default_factory=ExtractedField
    )

    currency: ExtractedField = Field(
        default_factory=ExtractedField
    )

    periods: list[FinancialStatementPeriod] = Field(
        default_factory=list
    )

    line_items: list[TableRow] = Field(
        default_factory=list
    )

    additional_fields: dict[str, ExtractedField] = Field(
        default_factory=dict
    )

    additional_tables: list[TableRow] = Field(
        default_factory=list
    )



class ProfitLossExtraction(BaseModel):
    """
    Structured extraction for a Profit & Loss statement.

    Comparative periods are stored independently so that
    financial validation can be performed for each period.
    """

    document_type: Literal["profit_and_loss"] = (
        "profit_and_loss"
    )

    statement_title: ExtractedField = Field(
        default_factory=ExtractedField
    )

    statement_date: ExtractedField = Field(
        default_factory=ExtractedField
    )

    currency: ExtractedField = Field(
        default_factory=ExtractedField
    )

    periods: list[FinancialStatementPeriod] = Field(
        default_factory=list
    )

    line_items: list[TableRow] = Field(
        default_factory=list
    )

    additional_fields: dict[str, ExtractedField] = Field(
        default_factory=dict
    )

    additional_tables: list[TableRow] = Field(
        default_factory=list
    )



class CashFlowExtraction(BaseModel):
    """
    Structured extraction for a Cash Flow Statement.

    Comparative periods are stored independently.
    """

    document_type: Literal["cash_flow"] = (
        "cash_flow"
    )

    statement_title: ExtractedField = Field(
        default_factory=ExtractedField
    )

    statement_date: ExtractedField = Field(
        default_factory=ExtractedField
    )

    currency: ExtractedField = Field(
        default_factory=ExtractedField
    )

    periods: list[FinancialStatementPeriod] = Field(
        default_factory=list
    )

    line_items: list[TableRow] = Field(
        default_factory=list
    )

    additional_fields: dict[str, ExtractedField] = Field(
        default_factory=dict
    )

    additional_tables: list[TableRow] = Field(
        default_factory=list
    )



class ExtractionResult(BaseModel):
    """
    Top-level structured extraction result.

    document_type is supplied by the frontend/request metadata.
    Automatic document classification is intentionally not used.
    """

    document_type: Literal[
        "invoice",
        "balance_sheet",
        "profit_and_loss",
        "cash_flow",
        "cash_flow_statement"
    ]

    data: (
        InvoiceExtraction
        | BalanceSheetExtraction
        | ProfitLossExtraction
        | CashFlowExtraction
    )

    raw_text: str | None = None

    pages: list[dict[str, Any]] = Field(
        default_factory=list
    )