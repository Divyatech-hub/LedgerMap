from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

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


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: Literal["user", "assistant"]
    text: str
    candidates: list[ChatCandidate] | None
    created_at: datetime
