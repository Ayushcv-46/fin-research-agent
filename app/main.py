import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas import ReportRequest
from agents.graph import build_graph
from db.persistence import save_report, get_reports, get_report_by_id
from db.health import check_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
GRAPH = build_graph()


@app.post("/report")
def create_report(request: ReportRequest):
    if not request.ticker or not request.ticker.isalpha():
        raise HTTPException(status_code=400, detail="Invalid ticker symbol.")

    logger.info(f"Starting report generation for {request.ticker}")
    try:
        initial_state = {
            "ticker": request.ticker,
            "question": request.question,
            "current_query": request.question,
            "judge_mode": request.judge_mode,
        }
        result = GRAPH.invoke(initial_state)
        save_report(result)
        logger.info(f"Report saved for {request.ticker}")
        return result

    except TimeoutError:
        logger.error(f"Timeout generating report for {request.ticker}")
        raise HTTPException(status_code=503, detail="The AI service timed out. Please try again.")

    except Exception as e:
        logger.error(f"Unexpected error for {request.ticker}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.get("/report/stream")
def report_stream(ticker: str, question: str, judge_mode: str = "api"):
    def event_generator():
        logger.info(f"Starting streamed report for {ticker}")
        yield f"event: stage\ndata: {json.dumps({'stage': 'data', 'message': 'Fetching SEC filing...'})}\n\n"

        initial_state = {
            "ticker": ticker,
            "question": question,
            "current_query": question,
            "judge_mode": judge_mode,
        }

        try:
            for chunk in GRAPH.stream(initial_state):
                node_name = list(chunk.keys())[0]
                yield f"event: stage\ndata: {json.dumps({'stage': node_name, 'message': f'Running {node_name}...'})}\n\n"

            final_state = GRAPH.invoke(initial_state)
            save_report(final_state)
            logger.info(f"Streamed report saved for {ticker}")
            yield f"event: complete\ndata: {json.dumps(final_state)}\n\n"

        except Exception as e:
            logger.error(f"Streaming error for {ticker}: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/reports")
def list_reports():
    return get_reports()


@app.get("/reports/{report_id}")
def get_one_report(report_id: int):
    report = get_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/health")
def health_check():
    db_ok = check_db_connection()
    return {"status": "ok" if db_ok else "error", "database": db_ok}