from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ledgermap.db.repositories import clients as clients_repo
from ledgermap.db.repositories import mappings as mappings_repo
from ledgermap.db.repositories import runs as runs_repo
from ledgermap.db.session import get_session
from ledgermap.schemas.runs import CorrectionCreate, CorrectionRead, RunRead
from ledgermap.services.matching import normalize_name
from ledgermap.services.run_pipeline import process_workbook

router = APIRouter(prefix="/runs")


def _run_to_read(run) -> RunRead:  # noqa: ANN001 - Run is a SQLAlchemy model
    total_rows = len(run.line_items)
    resolved_rows = sum(1 for item in run.line_items if item.matched_code is not None)
    return RunRead(
        id=run.id,
        client_id=run.client_id,
        period=run.period,
        status=run.status,
        source_type=run.source_type,
        original_filename=run.original_filename,
        created_at=run.created_at,
        completed_at=run.completed_at,
        total_rows=total_rows,
        resolved_rows=resolved_rows,
        review_rows=total_rows - resolved_rows,
        line_items=run.line_items,
    )


@router.post("/clients/{client_id}", response_model=RunRead, status_code=201)
async def create_run(
    client_id: int,
    period: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> RunRead:
    """Upload a trial balance for a client and persist a reviewable run.

    Resolves each leaf account against the client's persisted mapping memory
    (falling back to the workbook's own IFRS mapping sheet for bootstrapping),
    then writes the run and its line items to the database instead of just
    returning an in-memory preview.
    """
    client = await clients_repo.get_client(session, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")

    content = await file.read()
    persisted_mappings = await mappings_repo.get_mapping_memory(session, client_id)
    preview = process_workbook(content, persisted_mappings=persisted_mappings)

    run = await runs_repo.create_run(
        session,
        client_id=client_id,
        period=period,
        source_type=preview.source_type.value,
        original_filename=file.filename,
    )
    await runs_repo.add_line_items(
        session,
        run_id=run.id,
        line_items=[
            {
                "raw_name": item.node.name,
                "amount": item.node.amount,
                "row_number": item.node.row_number,
                "ancestors": list(item.node.ancestors),
                "matched_code": item.candidate.code,
                "confidence": Decimal(str(item.candidate.confidence)),
                "method": item.candidate.method.value,
                "status": "resolved" if item.candidate.code is not None else "review",
                "review_reason": item.candidate.review_reason,
            }
            for item in preview.line_items
        ],
    )
    await session.commit()

    persisted_run = await runs_repo.get_run(session, run.id)
    return _run_to_read(persisted_run)


@router.get("/{run_id}", response_model=RunRead)
async def get_run(run_id: int, session: AsyncSession = Depends(get_session)) -> RunRead:
    run = await runs_repo.get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return _run_to_read(run)


@router.post(
    "/{run_id}/line-items/{line_item_id}/corrections",
    response_model=CorrectionRead,
    status_code=201,
)
async def correct_line_item(
    run_id: int,
    line_item_id: int,
    payload: CorrectionCreate,
    session: AsyncSession = Depends(get_session),
) -> CorrectionRead:
    """Apply a manual correction to one line item and write it back into
    the client's persistent mapping memory, so the same account is never
    asked about twice.
    """
    line_item = await runs_repo.get_line_item(session, run_id, line_item_id)
    if line_item is None:
        raise HTTPException(status_code=404, detail="line item not found")

    run = await runs_repo.get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    correction = await runs_repo.apply_correction(
        session,
        line_item=line_item,
        resulting_code=payload.resulting_code,
        chat_message=payload.chat_message,
        corrected_by=payload.corrected_by,
    )
    await mappings_repo.upsert_mapping(
        session,
        client_id=run.client_id,
        raw_name=line_item.raw_name,
        normalized_raw_name=normalize_name(line_item.raw_name),
        ancestor_context="|".join(line_item.ancestors),
        code=payload.resulting_code,
        method="human_correction",
        approved_by=payload.corrected_by,
    )
    await session.commit()
    return CorrectionRead.model_validate(correction)
