"""Aggregate persisted runs into the Detailed MIS preview shape.

The README's product surface calls for "the full Detailed MIS (all
historical columns + new month) rendered as a table, new column's cells
color-coded by resolution method". This module builds that grid from
whatever completed runs a client has, without touching the workbook
export itself (that's a separate, later step: writing the real .xlsx).
"""

from dataclasses import dataclass, field
from decimal import Decimal

from ledgermap.db.models import Run

# Mirrors the priority used to color a cell when a code's rows resolved by
# more than one method within a single run: show the least-confident method
# present, since that's what still deserves a human's attention.
_METHOD_PRIORITY = {"review": 0, "fuzzy": 1, "inherited": 1, "corrected": 2, "exact": 3}


@dataclass(frozen=True)
class MisCell:
    amount: Decimal
    method: str
    """The lowest-confidence method among the line items rolled into this
    cell; drives the frontend's color-coding for this period's column."""


@dataclass(frozen=True)
class MisRow:
    code: str
    description: str | None
    cells: dict[str, MisCell] = field(default_factory=dict)
    """Keyed by period; a period with no activity for this code is absent."""


@dataclass(frozen=True)
class MisReport:
    periods: list[str]
    rows: list[MisRow]
    unresolved_periods: list[str]
    """Periods that have at least one line item still awaiting review —
    surfaced so the UI can flag a column as incomplete."""


def build_mis_report(
    runs: list[Run], taxonomy: dict[str, str] | None = None
) -> MisReport:
    """Build a code x period grid from a client's completed runs.

    `runs` must already be ordered oldest-to-newest (see
    `list_runs_for_client_with_line_items`). Line items with no resolved
    code are excluded from the grid itself, but their run's period is still
    reported in `unresolved_periods`.
    """
    taxonomy = taxonomy or {}
    periods = [run.period for run in runs]
    unresolved_periods = [
        run.period
        for run in runs
        if any(item.matched_code is None for item in run.line_items)
    ]

    # code -> period -> (summed amount, weakest method seen)
    grid: dict[str, dict[str, tuple[Decimal, str]]] = {}
    for run in runs:
        per_code: dict[str, tuple[Decimal, str]] = {}
        for item in run.line_items:
            if item.matched_code is None:
                continue
            amount, method = per_code.get(item.matched_code, (Decimal(0), item.method))
            amount += item.amount
            if _METHOD_PRIORITY.get(item.method, 0) < _METHOD_PRIORITY.get(method, 0):
                method = item.method
            per_code[item.matched_code] = (amount, method)

        for code, (amount, method) in per_code.items():
            grid.setdefault(code, {})[run.period] = (amount, method)

    rows = [
        MisRow(
            code=code,
            description=taxonomy.get(code),
            cells={
                period: MisCell(amount=amount, method=method)
                for period, (amount, method) in by_period.items()
            },
        )
        for code, by_period in sorted(grid.items())
    ]

    return MisReport(periods=periods, rows=rows, unresolved_periods=unresolved_periods)
