from enum import StrEnum


class RunStatus(StrEnum):
    CREATED = "created"
    PROCESSING = "processing"
    REVIEW = "review"
    FINALIZED = "finalized"
    FAILED = "failed"