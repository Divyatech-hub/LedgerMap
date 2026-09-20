from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ledgermap.db.models import Correction, Run, RunLineItem


async def create_run(
    session: AsyncSession,
    *,
    client_id: int,
    period: str,
    source_type: str,
    original_filename: str | None,
) -> Run:
    run = Run(
        client_id=client_id,
        period=period,
        source_type=source_type,
        original_filename=original_filename,
        status="completed",
        completed_at=datetime.now(UTC),
    )
    session.add(run)
    await session.flush()
    return run


async def add_line_items(
    session: AsyncSession, *, run_id: int, line_items: list[dict]
) -> list[RunLineItem]:
    rows = [RunLineItem(run_id=run_id, **fields) for fields in line_items]
    session.add_all(rows)
    await session.flush()
    return rows


async def get_run(session: AsyncSession, run_id: int) -> Run | None:
    result = await session.execute(
        select(Run)
        .where(Run.id == run_id)
        .options(selectinload(Run.line_items))
    )
    return result.scalar_one_or_none()


async def get_completed_run_for_period(
    session: AsyncSession, *, client_id: int, period: str
) -> Run | None:
    result = await session.execute(
        select(Run).where(
            Run.client_id == client_id,
            Run.period == period,
            Run.status == "completed",
        )
    )
    return result.scalar_one_or_none()


async def list_runs_for_client(session: AsyncSession, client_id: int) -> list[Run]:
    result = await session.execute(
        select(Run).where(Run.client_id == client_id).order_by(Run.created_at.desc())
    )
    return list(result.scalars().all())


async def list_runs_for_client_with_line_items(
    session: AsyncSession, client_id: int
) -> list[Run]:
    """Completed runs for a client, oldest to newest, with line items loaded.

    Oldest-first ordering matches how the Detailed MIS reads: historical
    columns on the left, the newest period on the right.
    """
    result = await session.execute(
        select(Run)
        .where(Run.client_id == client_id, Run.status == "completed")
        .options(selectinload(Run.line_items))
        .order_by(Run.period)
    )
    return list(result.scalars().all())


async def get_line_item(
    session: AsyncSession, run_id: int, line_item_id: int
) -> RunLineItem | None:
    result = await session.execute(
        select(RunLineItem).where(
            RunLineItem.id == line_item_id, RunLineItem.run_id == run_id
        )
    )
    return result.scalar_one_or_none()


async def apply_correction(
    session: AsyncSession,
    *,
    line_item: RunLineItem,
    resulting_code: str,
    chat_message: str | None,
    corrected_by: str | None,
    previous_code: str | None,
    is_conflict: bool,
) -> Correction:
    line_item.matched_code = resulting_code
    line_item.method = "corrected"
    line_item.status = "resolved"
    line_item.review_reason = None
    line_item.confidence = None

    correction = Correction(
        run_id=line_item.run_id,
        line_item_id=line_item.id,
        chat_message=chat_message,
        previous_code=previous_code,
        resulting_code=resulting_code,
        is_conflict=is_conflict,
        corrected_by=corrected_by,
    )
    session.add(correction)
    await session.flush()
    return correction
