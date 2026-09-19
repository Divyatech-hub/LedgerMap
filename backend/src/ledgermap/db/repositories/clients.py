from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ledgermap.db.models import Client


async def create_client(session: AsyncSession, *, name: str) -> Client:
    client = Client(name=name)
    session.add(client)
    await session.flush()
    return client


async def get_client(session: AsyncSession, client_id: int) -> Client | None:
    return await session.get(Client, client_id)


async def list_clients(session: AsyncSession) -> list[Client]:
    result = await session.execute(select(Client).order_by(Client.name))
    return list(result.scalars().all())
