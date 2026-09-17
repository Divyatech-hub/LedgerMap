from collections.abc import Iterable
import re

from ledgermap.domain.models import SourceType

ERP_HEADERS = {
    "g/l period",
    "fiscal year",
    "trail balance by company division object",
}
FREE_TEXT_HEADERS = {"particulars", "opening", "closing"}
CODE_PATTERN = re.compile(r"^\d{4,10}$")


def detect_source_type(headers: Iterable[object], account_codes: Iterable[object]) -> SourceType:
    normalized_headers = {str(value).strip().lower() for value in headers if value}
    if normalized_headers & ERP_HEADERS:
        return SourceType.ERP

    values = [str(value).strip() for value in account_codes if value not in (None, "")]
    if values and sum(bool(CODE_PATTERN.fullmatch(value)) for value in values) / len(values) >= 0.8:
        return SourceType.ERP
    if values:
        return SourceType.FREE_TEXT_LEDGER
    if normalized_headers & FREE_TEXT_HEADERS:
        return SourceType.FREE_TEXT_LEDGER
    return SourceType.UNKNOWN