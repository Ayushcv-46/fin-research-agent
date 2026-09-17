from pydantic import BaseModel

class ReportRequest(BaseModel):
    ticker: str
    question: str