import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.schemas import ReportRequest
from agents.graph import build_graph
from db.persistence import save_report, get_reports, get_report_by_id
from db.health import check_db_connection
from retrieval.embedder import warm_up_embedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Warming up SentenceTransformer embedder on server startup...")
    warm_up_embedder()
    logger.info("Embedder warm-up complete.")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GRAPH = build_graph()


def validate_ticker(ticker: str) -> str:
    cleaned = ticker.strip().upper() if ticker else ""
    if not cleaned or not cleaned.isalpha():
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker symbol. Ticker must contain alphabetic characters only."
        )
    return cleaned


@app.post("/report")
def create_report(request: ReportRequest):
    ticker = validate_ticker(request.ticker)
    logger.info("Starting synchronous report generation for %s", ticker)

    try:
        initial_state = {
            "ticker": ticker,
            "question": request.question,
            "current_query": request.question,
            "judge_mode": request.judge_mode,
        }
        result = GRAPH.invoke(initial_state)
        save_report(result)
        logger.info("Report saved successfully for %s", ticker)
        return result

    except RuntimeError as e:
        logger.exception("Pipeline runtime error generating report for %s: %s", ticker, e)
        raise HTTPException(
            status_code=502,
            detail="Upstream AI provider error occurred while generating report. Please try again."
        ) from e

    except TimeoutError as e:
        logger.error("Timeout generating report for %s: %s", ticker, e)
        raise HTTPException(
            status_code=504,
            detail="The AI research service timed out. Please try again."
        ) from e

    except Exception as e:
        logger.exception("Unexpected error generating report for %s: %s", ticker, e)
        raise HTTPException(
            status_code=500,
            detail="An unexpected internal error occurred."
        ) from e


@app.get("/report/stream")
def report_stream(ticker: str, question: str, judge_mode: str = "api"):
    validated_ticker = validate_ticker(ticker)

    def event_generator():
        logger.info("Starting streamed report generation for %s", validated_ticker)
        yield f"event: stage\ndata: {json.dumps({'stage': 'data', 'message': 'Fetching SEC filing & market data...'})}\n\n"

        initial_state = {
            "ticker": validated_ticker,
            "question": question,
            "current_query": question,
            "judge_mode": judge_mode,
        }

        try:
            final_state = dict(initial_state)
            for chunk in GRAPH.stream(initial_state):
                for node_name, node_output in chunk.items():
                    if isinstance(node_output, dict):
                        final_state.update(node_output)
                    yield f"event: stage\ndata: {json.dumps({'stage': node_name, 'message': f'Running {node_name}...'})}\n\n"

            save_report(final_state)
            logger.info("Streamed report saved to database for %s", validated_ticker)

            ui_payload = {
                "ticker": final_state.get("ticker"),
                "question": final_state.get("question"),
                "final_report": final_state.get("final_report"),
                "judge_score": final_state.get("judge_score"),
                "price_data": final_state.get("price_data"),
                "fundamentals": final_state.get("fundamentals"),
                "confidence_label": final_state.get("confidence_label"),
                "confidence_reasoning": final_state.get("confidence_reasoning"),
                "retry_count": final_state.get("retry_count", 0),
            }
            yield f"event: complete\ndata: {json.dumps(ui_payload)}\n\n"

        except Exception as e:
            logger.exception("Streaming error occurred for %s: %s", validated_ticker, e)
            yield f"event: error\ndata: {json.dumps({'message': 'An error occurred while generating the research report. Please try again.'})}\n\n"

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