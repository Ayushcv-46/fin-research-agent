# Database models
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    ticker = Column(String, nullable=False)
    question = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    final_report = Column(String)
    grounding = Column(Float)
    completeness = Column(Float)
    clarity = Column(Float)
    overall = Column(Float)
    retrieval_mode = Column(String)
    judge_mode = Column(String)