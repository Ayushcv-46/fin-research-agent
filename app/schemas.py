from typing import Literal
from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    ticker: str
    question: str = Field(..., min_length=1, max_length=500)
    judge_mode: Literal["api", "finetuned"] = "api"