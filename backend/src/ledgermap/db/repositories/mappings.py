from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ledgermap.db.models import AccountMapping


async def get_mapping_memory(
    session: AsyncSession, client_id: int
) -> dict[str, str | None]:
    """Return this client's persisted mapping memory as normalized_name -> code.

    Ancestor context is not part of the lookup key here; the matcher only needs
    a name -> code table. Rows without an approved code are skipped.
    """
    result = await session.execute(
        select(AccountMapping.normalized_raw_name, AccountMapping.code).where(
            AccountMapping.client_id == client_id,
            AccountMapping.code.is_not(None),
        )
    )
    return {normalized: code for normalized, code in result.all()}


async def upsert_mapping(
    session: AsyncSession,
    *,
    client_id: int,
    raw_name: str,
    normalized_raw_name: str,
    ancestor_context: str,
    code: str,
    method: str,
    confidence: float | None = None,
    approved_by: str | None = None,
) -> AccountMapping:
    """Insert or update the mapping for (client, normalized name, ancestor context).

    A human correction always wins going forward: this is how corrections close
    the loop into persistent mapping memory per the product's core design.
    """
    now = datetime.now(UTC)
    stmt = (
        pg_insert(AccountMapping)
        .values(
            client_id=client_id,
            raw_name=raw_name,
            normalized_raw_name=normalized_raw_name,
            ancestor_context=ancestor_context,
            code=code,
            confidence=confidence,
            method=method,
            approved_by=approved_by,
            last_seen=now,
        )
        .on_conflict_do_update(
            constraint="uq_client_account_mapping_context",
            set_={
                "raw_name": raw_name,
                "code": code,
                "confidence": confidence,
                "method": method,
                "approved_by": approved_by,
                "last_seen": now,
            },
        )
        .returning(AccountMapping)
    )
    result = await session.execute(stmt)
    await session.flush()
    return result.scalar_one()
