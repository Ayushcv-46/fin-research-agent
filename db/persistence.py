# Database persistence layer
from db.session import SessionLocal
from db.models import Report

def save_report(graph_state: dict) -> Report:
    judge_score = graph_state.get("judge_score") or {}


    report = Report(
        ticker=graph_state.get("ticker"),
        company_name=graph_state.get("company_name"),
        question=graph_state.get("question"),
        final_report=graph_state.get("final_report"),
        grounding=judge_score.get("grounding", -1),
        completeness=judge_score.get("completeness", -1),
        clarity=judge_score.get("clarity", -1),
        overall=judge_score.get("overall", -1),
        retrieval_mode=graph_state.get("retrieval_mode"),
        judge_mode=graph_state.get("judge_mode"),
    )

    session = SessionLocal()
    try:
        session.add(report)
        session.commit()
        session.refresh(report)
        return report
    finally:
        session.close()
def get_reports(limit: int = 20) -> list[Report]:
    session = SessionLocal()
    try:
        return session.query(Report).order_by(Report.timestamp.desc()).limit(limit).all()
    finally:
        session.close()


def get_report_by_id(report_id: int) -> Report | None:
    session = SessionLocal()
    try:
        return session.query(Report).filter(Report.id == report_id).first()
    finally:
        session.close()


def report_payload(report: Report) -> dict:
    """Return stable fields used by history/details responses."""
    return {
        "id": report.id,
        "ticker": report.ticker,
        "company_name": getattr(report, "company_name", None),
        "question": report.question,
        "timestamp": report.timestamp,
        "final_report": report.final_report,
        "grounding": report.grounding,
        "completeness": report.completeness,
        "clarity": report.clarity,
        "overall": report.overall,
    }
