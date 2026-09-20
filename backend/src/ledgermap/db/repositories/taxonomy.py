from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ledgermap.db.models import Taxonomy, TaxonomyEntry

# One taxonomy per client for now — the Detailed MIS's code list as of the
# most recent upload that had one. Taxonomy is a table (not a single column
# on Client) so a future pass can version it over time without a migration.
_DEFAULT_TAXONOMY_NAME = "default"


async def get_taxonomy_codes(session: AsyncSession, client_id: int) -> dict[str, str]:
    """This client's current taxonomy as code -> description, or {} if none
    has ever been extracted for them yet."""
    result = await session.execute(
        select(Taxonomy)
        .where(Taxonomy.client_id == client_id, Taxonomy.name == _DEFAULT_TAXONOMY_NAME)
        .options(selectinload(Taxonomy.entries))
    )
    taxonomy = result.scalar_one_or_none()
    if taxonomy is None:
        return {}
    return {entry.code: entry.description for entry in taxonomy.entries}


async def upsert_taxonomy(
    session: AsyncSession, *, client_id: int, entries: dict[str, str]
) -> Taxonomy:
    """Replace this client's taxonomy entries with the given code -> description
    map. Called on every upload that has a Detailed MIS sheet to extract from,
    so the taxonomy tracks the client's own file as it evolves (new codes
    added over time are picked up; nothing here removes codes that later
    uploads no longer mention, since old runs may still reference them)."""
    result = await session.execute(
        select(Taxonomy).where(
            Taxonomy.client_id == client_id, Taxonomy.name == _DEFAULT_TAXONOMY_NAME
        )
    )
    taxonomy = result.scalar_one_or_none()
    if taxonomy is None:
        taxonomy = Taxonomy(client_id=client_id, name=_DEFAULT_TAXONOMY_NAME)
        session.add(taxonomy)
        await session.flush()

    if not entries:
        return taxonomy

    stmt = pg_insert(TaxonomyEntry).values(
        [
            {"taxonomy_id": taxonomy.id, "code": code, "description": description}
            for code, description in entries.items()
        ]
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_taxonomy_entry_code",
        set_={"description": stmt.excluded.description},
    )
    await session.execute(stmt)
    await session.flush()
    return taxonomy
