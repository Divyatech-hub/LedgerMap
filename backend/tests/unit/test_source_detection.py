from ledgermap.domain.models import SourceType
from ledgermap.services.source_detection import detect_source_type


def test_erp_header_wins() -> None:
    assert detect_source_type(["Fiscal Year", "Amount"], []) is SourceType.ERP


def test_numeric_codes_identify_erp_export() -> None:
    assert detect_source_type(["Account", "Amount"], ["411001", "411002"]) is SourceType.ERP


def test_free_text_accounts_use_ledger_path() -> None:
    assert detect_source_type(["Account", "Amount"], ["Office rent", "Bank OD A/c"]) is SourceType.FREE_TEXT_LEDGER


def test_tally_headers_identify_free_text_without_codes() -> None:
    assert detect_source_type(["Particulars", "Opening", "Closing"], []) is SourceType.FREE_TEXT_LEDGER