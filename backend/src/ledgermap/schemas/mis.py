from decimal import Decimal

from pydantic import BaseModel


class MisCellRead(BaseModel):
    amount: Decimal
    method: str


class MisRowRead(BaseModel):
    code: str
    description: str | None
    cells: dict[str, MisCellRead]


class MisReportRead(BaseModel):
    periods: list[str]
    rows: list[MisRowRead]
    unresolved_periods: list[str]
