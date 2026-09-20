from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ledgermap.db.repositories import clients as clients_repo
from ledgermap.db.repositories import runs as runs_repo
from ledgermap.db.repositories import taxonomy as taxonomy_repo
from ledgermap.db.session import get_session
from ledgermap.schemas.clients import ClientCreate, ClientRead
from ledgermap.schemas.mis import MisReportRead
from ledgermap.schemas.runs import RunSummary
from ledgermap.services.mis_report import build_mis_report

router = APIRouter(prefix="/clients")


@router.post("", response_model=ClientRead, status_code=201)
async def create_client(
    payload: ClientCreate, session: AsyncSession = Depends(get_session)
) -> ClientRead:
    client = await clients_repo.create_client(session, name=payload.name)
    await session.commit()
    return ClientRead.model_validate(client)


@router.get("", response_model=list[ClientRead])
async def list_clients(
    session: AsyncSession = Depends(get_session),
) -> list[ClientRead]:
    clients = await clients_repo.list_clients(session)
    return [ClientRead.model_validate(client) for client in clients]


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(
    client_id: int, session: AsyncSession = Depends(get_session)
) -> ClientRead:
    client = await clients_repo.get_client(session, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    return ClientRead.model_validate(client)


@router.get("/{client_id}/runs", response_model=list[RunSummary])
async def list_client_runs(
    client_id: int, session: AsyncSession = Depends(get_session)
) -> list[RunSummary]:
    client = await clients_repo.get_client(session, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    runs = await runs_repo.list_runs_for_client(session, client_id)
    return [RunSummary.model_validate(run) for run in runs]


@router.get("/{client_id}/mis", response_model=MisReportRead)
async def get_client_mis_report(
    client_id: int, session: AsyncSession = Depends(get_session)
) -> MisReportRead:
    """The Detailed MIS preview: every completed run's line items rolled up
    by code, one column per period, oldest to newest.
    """
    client = await clients_repo.get_client(session, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    runs = await runs_repo.list_runs_for_client_with_line_items(session, client_id)
    taxonomy = await taxonomy_repo.get_taxonomy_codes(session, client_id)
    report = build_mis_report(runs, taxonomy=taxonomy)
    return MisReportRead.model_validate(report, from_attributes=True)
