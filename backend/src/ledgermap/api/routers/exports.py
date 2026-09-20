from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ledgermap.db.repositories import clients as clients_repo
from ledgermap.db.repositories import runs as runs_repo
from ledgermap.db.repositories import taxonomy as taxonomy_repo
from ledgermap.db.session import get_session
from ledgermap.services.mis_export import build_mis_workbook

router = APIRouter(prefix="/exports")

_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/clients/{client_id}/mis")
async def export_client_mis(
    client_id: int, session: AsyncSession = Depends(get_session)
) -> Response:
    """Download the Detailed MIS as a real .xlsx: a summary sheet with live
    SUMIF formulas, and one line-items sheet per period for the accountant
    to trace any total back to its source rows.
    """
    client = await clients_repo.get_client(session, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")

    runs = await runs_repo.list_runs_for_client_with_line_items(session, client_id)
    if not runs:
        raise HTTPException(status_code=404, detail="no completed runs to export")

    taxonomy = await taxonomy_repo.get_taxonomy_codes(session, client_id)
    workbook_bytes = build_mis_workbook(runs, taxonomy=taxonomy)

    filename = f"{client.name} - Detailed MIS.xlsx".replace("/", "-")
    return Response(
        content=workbook_bytes,
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
