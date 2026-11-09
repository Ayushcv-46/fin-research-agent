from typing import Literal
from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    ticker: str | None = None
    company_name: str | None = None
    question: str = Field(..., min_length=1, max_length=500)
    judge_mode: Literal["api", "finetuned"] = "api"
    search_mode: Literal["dense", "bm25", "hybrid"] = "hybrid"
    retrieval_mode: Literal["fixed", "adaptive"] = "fixed"
    langsmith_tracing: bool = False
