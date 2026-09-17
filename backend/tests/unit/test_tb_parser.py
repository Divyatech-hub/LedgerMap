from decimal import Decimal

from ledgermap.domain.models import TrialBalanceRow
from ledgermap.services.tb_parser import parse_rows


def test_parser_excludes_group_headers_and_footers() -> None:
    nodes = parse_rows(
        [
            TrialBalanceRow("Current Assets", Decimal("100"), depth=0, is_bold=True),
            TrialBalanceRow("Cash-in-Hand", Decimal("100"), depth=1),
            TrialBalanceRow("Grand Total", Decimal("100"), depth=0),
        ]
    )

    assert [node.name for node in nodes] == ["Current Assets", "Cash-in-Hand"]
    assert nodes[0].is_group is True
    assert nodes[1].ancestors == ("Current Assets",)


def test_customer_detail_is_marked_as_rollup_detail() -> None:
    nodes = parse_rows(
        [
            TrialBalanceRow("Current Liabilities", Decimal("100"), depth=0),
            TrialBalanceRow("KAUST", Decimal("100"), depth=1),
        ]
    )

    assert nodes[1].is_rollup_detail is True