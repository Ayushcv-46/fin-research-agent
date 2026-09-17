from fastapi import FastAPI
from app.schemas import ReportRequest
from agents.graph import build_graph
from db.persistence import save_report, get_reports, get_report_by_id
from db.health import check_db_connection

app = FastAPI()
GRAPH = build_graph()


@app.post("/report")
def create_report(request: ReportRequest):
    initial_state = {
        "ticker": request.ticker,
        "question": request.question,
        "current_query": request.question,
    }
    result = GRAPH.invoke(initial_state)
    save_report(result)
    return result


@app.get("/reports")
def list_reports():
    return get_reports()


@app.get("/reports/{report_id}")
def get_one_report(report_id: int):
    report = get_report_by_id(report_id)
    if report is None:
        return {"error": "Report not found"}
    return report


@app.get("/health")
def health_check():
    db_ok = check_db_connection()
    return {"status": "ok" if db_ok else "error", "database": db_ok}