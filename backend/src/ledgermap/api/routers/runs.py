from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ledgermap.config import get_settings
from ledgermap.db.models import Correction, RunLineItem
from ledgermap.db.repositories import clients as clients_repo
from ledgermap.db.repositories import mappings as mappings_repo
from ledgermap.db.repositories import runs as runs_repo
from ledgermap.db.repositories import taxonomy as taxonomy_repo
from ledgermap.db.session import get_session
from ledgermap.integrations.llm.chat_correction import (
    ChatCorrectionRequest,
    ChatLineItemSummary,
)
from ledgermap.schemas.chat import (
    ChatCandidate,
    ChatCorrectionCreate,
    ChatCorrectionResponse,
)
from ledgermap.schemas.runs import CorrectionCreate, CorrectionRead, RunRead
from ledgermap.services.llm_review import classify_reviews_with_llm
from ledgermap.services.matching import normalize_name
from ledgermap.services.run_pipeline import process_workbook
from ledgermap.services.taxonomy import extract_taxonomy

router = APIRouter(prefix="/runs")


async def _apply_correction(
    session: AsyncSession,
    *,
    line_item: RunLineItem,
    client_id: int,
    resulting_code: str,
    chat_message: str | None,
    corrected_by: str | None,
) -> Correction:
    upsert_result = await mappings_repo.upsert_mapping(
        session,
        client_id=client_id,
        raw_name=line_item.raw_name,
        normalized_raw_name=normalize_name(line_item.raw_name),
        ancestor_context="|".join(line_item.ancestors),
        code=resulting_code,
        method="human_correction",
        approved_by=corrected_by,
    )
    return await runs_repo.apply_correction(
        session,
        line_item=line_item,
        resulting_code=resulting_code,
        chat_message=chat_message,
        corrected_by=corrected_by,
        previous_code=upsert_result.previous_code,
        is_conflict=upsert_result.is_conflict,
    )


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
    line_items = preview.line_items

    try:
        extracted_taxonomy = extract_taxonomy(content)
    except (KeyError, ValueError):
        extracted_taxonomy = {}
    if extracted_taxonomy:
        await taxonomy_repo.upsert_taxonomy(
            session, client_id=client_id, entries=extracted_taxonomy
        )

    if get_settings().llm_classification_enabled:
        taxonomy = await taxonomy_repo.get_taxonomy_codes(session, client_id)
        if taxonomy:
            from ledgermap.integrations.llm.anthropic_classifier import (
                classify_with_anthropic,
            )

            line_items = await classify_reviews_with_llm(
                line_items, taxonomy=taxonomy, classify=classify_with_anthropic
            )

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
            for item in line_items
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

    correction = await _apply_correction(
        session,
        line_item=line_item,
        client_id=run.client_id,
        resulting_code=payload.resulting_code,
        chat_message=payload.chat_message,
        corrected_by=payload.corrected_by,
    )
    await session.commit()
    return CorrectionRead.model_validate(correction)


@router.post("/{run_id}/chat", response_model=ChatCorrectionResponse)
async def chat_correct_run(
    run_id: int,
    payload: ChatCorrectionCreate,
    session: AsyncSession = Depends(get_session),
) -> ChatCorrectionResponse:
    """Interpret a plain-language correction request against this run's
    current line items. Applies it immediately when the model confidently
    identifies exactly one target and a valid code (same effect as a manual
    correction); otherwise returns candidate line items for the accountant
    to choose from instead of guessing.
    """
    if not get_settings().llm_classification_enabled:
        raise HTTPException(
            status_code=503,
            detail="chat corrections require LLM classification to be enabled",
        )

    run = await runs_repo.get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    taxonomy = await taxonomy_repo.get_taxonomy_codes(session, run.client_id)
    if not taxonomy:
        raise HTTPException(
            status_code=422,
            detail="client has no known taxonomy to correct against yet",
        )

    from ledgermap.integrations.llm.anthropic_chat_correction import (
        interpret_chat_correction_with_anthropic,
    )

    result = await interpret_chat_correction_with_anthropic(
        ChatCorrectionRequest(
            message=payload.message,
            line_items=tuple(
                ChatLineItemSummary(
                    id=item.id,
                    raw_name=item.raw_name,
                    ancestors=tuple(item.ancestors),
                    matched_code=item.matched_code,
                )
                for item in run.line_items
            ),
            taxonomy=taxonomy,
        )
    )

    if result.line_item_id is None or result.resulting_code is None:
        candidates_by_id = {item.id: item for item in run.line_items}
        return ChatCorrectionResponse(
            applied=False,
            explanation=result.explanation,
            candidates=[
                ChatCandidate(
                    id=item.id,
                    raw_name=item.raw_name,
                    ancestors=item.ancestors,
                    matched_code=item.matched_code,
                )
                for candidate_id in result.candidate_ids
                if (item := candidates_by_id.get(candidate_id)) is not None
            ],
        )

    line_item = await runs_repo.get_line_item(session, run_id, result.line_item_id)
    if line_item is None:
        return ChatCorrectionResponse(
            applied=False,
            explanation="The identified line item no longer exists on this run.",
        )

    correction = await _apply_correction(
        session,
        line_item=line_item,
        client_id=run.client_id,
        resulting_code=result.resulting_code,
        chat_message=payload.message,
        corrected_by=payload.corrected_by,
    )
    await session.commit()
    return ChatCorrectionResponse(
        applied=True,
        explanation=result.explanation,
        correction=CorrectionRead.model_validate(correction),
    )
