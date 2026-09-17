from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class SourceType(StrEnum):
    ERP = "erp"
    FREE_TEXT_LEDGER = "free_text_ledger"
    UNKNOWN = "unknown"


class MappingMethod(StrEnum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    INHERITED = "inherited"
    REVIEW = "review"


@dataclass(frozen=True)
class TrialBalanceRow:
    name: str
    amount: Decimal
    row_number: int | None = None
    depth: int = 0
    is_bold: bool = False
    code: str | None = None


@dataclass(frozen=True)
class AccountNode:
    name: str
    amount: Decimal
    depth: int
    row_number: int | None = None
    ancestors: tuple[str, ...] = ()
    is_group: bool = False
    is_rollup_detail: bool = False


@dataclass(frozen=True)
class MappingCandidate:
    code: str | None
    confidence: float
    method: MappingMethod
    review_reason: str | None = None