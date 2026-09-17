from pathlib import Path

from ledgermap.domain.models import SourceType
from ledgermap.services.run_pipeline import process_workbook
from ledgermap.services.taxonomy import extract_taxonomy


FIXTURE = Path(__file__).parents[3] / "prototype" / "TB.xlsx"


def test_tb_fixture_produces_reviewable_preview() -> None:
    preview = process_workbook(FIXTURE)

    assert preview.source_type is SourceType.FREE_TEXT_LEDGER
    assert preview.line_items
    assert all(item.node.name.lower() != "grand total" for item in preview.line_items)
    assert any(item.candidate.code == "2068" for item in preview.line_items)


def test_taxonomy_can_be_extracted_from_mis_fixture() -> None:
    taxonomy = extract_taxonomy(Path(__file__).parents[3] / "prototype" / "TB.xlsx")

    assert taxonomy["2001"] == "CHANDRASEKAR Capital Account"
    assert "3001" in taxonomy