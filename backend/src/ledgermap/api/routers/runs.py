from fastapi import APIRouter, File, UploadFile

from ledgermap.schemas.runs import LineItemPreview, RunPreview as RunPreviewResponse
from ledgermap.services.run_pipeline import process_workbook

router = APIRouter(prefix="/runs")


@router.post("/preview", response_model=RunPreviewResponse)
async def preview_run(file: UploadFile = File(...)) -> RunPreviewResponse:
	content = await file.read()
	preview = process_workbook(content)
	line_items = [
		LineItemPreview(
			name=item.node.name,
			amount=item.node.amount,
			row_number=item.node.row_number,
			ancestors=item.node.ancestors,
			matched_code=item.candidate.code,
			confidence=item.candidate.confidence,
			method=item.candidate.method,
			review_reason=item.candidate.review_reason,
		)
		for item in preview.line_items
	]
	return RunPreviewResponse(
		source_type=preview.source_type,
		total_rows=len(line_items),
		resolved_rows=preview.resolved_rows,
		review_rows=len(line_items) - preview.resolved_rows,
		line_items=line_items,
	)