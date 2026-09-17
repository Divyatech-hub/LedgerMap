from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from ledgermap.domain.models import MappingMethod, SourceType


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