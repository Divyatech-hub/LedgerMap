from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

from ledgermap.domain.models import AccountNode, TrialBalanceRow

FOOTER_NAMES = {"grand total", "total", "total assets", "total liabilities"}
ROLLUP_PARENT_NAMES = {
    "current assets",
    "current liabilities",
    "sundry debtors",
    "sundry creditors",
    "accounts receivable",
    "accounts payable",
}


def parse_rows(rows: Iterable[TrialBalanceRow]) -> list[AccountNode]:
    materialized = list(rows)
    nodes: list[AccountNode] = []
    for index, row in enumerate(materialized):
        name = row.name.strip()
        if not name or name.lower() in FOOTER_NAMES:
            continue

        next_depth = materialized[index + 1].depth if index + 1 < len(materialized) else -1
        is_group = row.is_bold and (row.depth == 0 or next_depth > row.depth)
        ancestors = _ancestors(materialized, index)
        parent = ancestors[-1].lower() if ancestors else ""
        is_rollup_detail = (
            not is_group
            and bool(ancestors)
            and parent in ROLLUP_PARENT_NAMES
            and row.depth > 0
        )
        nodes.append(
            AccountNode(
                name=name,
                amount=row.amount,
                depth=row.depth,
                row_number=row.row_number,
                ancestors=ancestors,
                is_group=is_group,
                is_rollup_detail=is_rollup_detail,
            )
        )
    return nodes


def _ancestors(rows: list[TrialBalanceRow], index: int) -> tuple[str, ...]:
    current_depth = rows[index].depth
    ancestors: list[str] = []
    for row in reversed(rows[:index]):
        if not row.name.strip() or row.name.strip().lower() in FOOTER_NAMES:
            continue
        if row.depth < current_depth:
            ancestors.append(row.name.strip())
            current_depth = row.depth
    return tuple(reversed(ancestors))


def amount_from_value(value: object) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except InvalidOperation:
        return Decimal("0")