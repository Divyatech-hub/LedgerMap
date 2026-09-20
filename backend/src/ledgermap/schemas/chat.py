from pydantic import BaseModel

from ledgermap.schemas.runs import CorrectionRead


class ChatCorrectionCreate(BaseModel):
    message: str
    corrected_by: str | None = None


class ChatCandidate(BaseModel):
    id: int
    raw_name: str
    ancestors: list[str]
    matched_code: str | None


class ChatCorrectionResponse(BaseModel):
    applied: bool
    explanation: str
    correction: CorrectionRead | None = None
    candidates: list[ChatCandidate] = []
