# Database persistence layer
from db.session import SessionLocal
from db.models import Report

def save_report(graph_state: dict) -> Report:
    judge_score = graph_state.get("judge_score", {})

    report = Report(
        ticker=graph_state.get("ticker"),
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