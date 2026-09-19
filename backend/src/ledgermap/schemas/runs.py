from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from ledgermap.domain.models import MappingMethod, SourceType


class RunLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_name: str
    amount: Decimal
    row_number: int | None
    ancestors: list[str]
    matched_code: str | None
    confidence: Decimal | None
    method: str
    status: str
    review_reason: str | None


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    period: str
    status: str
    source_type: str | None
    original_filename: str | None
    created_at: datetime
    completed_at: datetime | None
    total_rows: int
    resolved_rows: int
    review_rows: int
    line_items: list[RunLineItemRead]


class RunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    period: str
    status: str
    source_type: str | None
    created_at: datetime


class CorrectionCreate(BaseModel):
    resulting_code: str
    chat_message: str | None = None
    corrected_by: str | None = None


class CorrectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    line_item_id: int
    resulting_code: str
    chat_message: str | None
    corrected_by: str | None
    created_at: datetime


class LineItemPreview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    amount: Decimal
    row_number: int | None
    ancestors: tuple[str, ...]
    matched_code: str | None
    confidence: float
    method: MappingMethod
    review_reason: str | None


class RunPreview(BaseModel):
    source_type: SourceType
    total_rows: int
    resolved_rows: int
    review_rows: int
    line_items: list[LineItemPreview]
