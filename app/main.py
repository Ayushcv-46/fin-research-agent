import json
import logging
import os
import re
from contextlib import asynccontextmanager
from typing import Literal

import openai
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agents.graph import build_graph
from app.schemas import ReportRequest
from db.health import check_db_connection
from db.persistence import get_report_by_id, get_reports, save_report, report_payload
from retrieval.embedder import warm_up_embedder
from retrieval import vector_store
from data.edgar_fetcher import HEADERS as SEC_HEADERS
from langchain_core.tracers.langchain import LangChainTracer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


GRAPH = build_graph()
_company_directory_cache: list[dict] | None = None


def migrate_legacy_chroma_indexes():
    """Copy old per-ticker indexes into a legacy namespace for compatibility."""
    for collection in vector_store._client.list_collections():
        if not collection.name.startswith("ticker_") or len(collection.name.split("_")) != 2:
            continue
        legacy = vector_store._client.get_collection(collection.name)
        if legacy.count() == 0:
            continue
        ticker = collection.name.removeprefix("ticker_").upper()
        records = legacy.get(include=["documents", "embeddings", "metadatas"])
        chunks = [
            {"text": doc, "embedding": embedding,
             "section": (metadata or {}).get("section", "Item General")}
            for doc, embedding, metadata in zip(records["documents"], records["embeddings"], records["metadatas"])
        ]
        vector_store.ingest_filing(ticker, chunks, "legacy", {"filing_date": "unknown", "report_date": "unknown"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Warming up SentenceTransformer embedder on server startup...")
    warm_up_embedder()
    migrate_legacy_chroma_indexes()
    logger.info("Embedder warm-up and legacy Chroma migration complete.")
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_ticker(ticker: str) -> str:
    cleaned = ticker.strip().upper() if ticker else ""
    if not cleaned or not re.fullmatch(r"[A-Z0-9.-]{1,15}", cleaned):
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker symbol.",
        )
    return cleaned


def _get_company_directory() -> list[dict]:
    global _company_directory_cache
    if _company_directory_cache is None:
        response = requests.get("https://www.sec.gov/files/company_tickers.json", headers=SEC_HEADERS, timeout=15)
        response.raise_for_status()
        _company_directory_cache = [
            {"ticker": str(entry["ticker"]).upper(), "name": entry["title"], "cik": str(entry["cik_str"]).zfill(10)}
            for entry in response.json().values()
        ]
    return _company_directory_cache


@app.get("/companies/search")
def search_companies(q: str = Query(..., min_length=1, max_length=100)):
    query = q.casefold().strip()
    try:
        directory = _get_company_directory()
        rows = [row for row in directory if row["ticker"].casefold() == query]
        if not rows:
            rows = [row for row in directory if query in row["name"].casefold()]
        return rows[:10]
    except Exception as exc:
        logger.exception("SEC company search failed: %s", exc)
        raise HTTPException(status_code=502, detail="Company search is temporarily unavailable.") from exc


def build_ui_payload(state: dict) -> dict:
    return {
        "ticker": state.get("ticker"),
        "company_name": state.get("company_name"),
        "question": state.get("question"),
        "final_report": state.get("final_report"),
        "judge_score": state.get("judge_score"),
        "price_data": state.get("price_data"),
        "fundamentals": state.get("fundamentals"),
        "confidence_label": state.get("confidence_label"),
        "confidence_reasoning": state.get("confidence_reasoning"),
        "retry_count": state.get("retry_count", 0),
        "judge_mode": state.get("judge_mode", "api"),
        "search_mode": state.get("search_mode", "hybrid"),
        "retrieval_mode": state.get("retrieval_mode", "adaptive"),
        "filing_metadata": state.get("filing_metadata", {}),
        "market_data_as_of": state.get("market_data_as_of"),
        "data_warnings": state.get("data_warnings", []),
        "langsmith_tracing": state.get("langsmith_tracing", False),
        "langsmith_trace_url": state.get("langsmith_trace_url"),
    }


def langsmith_api_key_configured() -> bool:
    return any(
        os.getenv(name, "").strip() and not os.getenv(name, "").strip().lower().startswith("your_")
        for name in ("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY")
    )


def create_langsmith_tracer(enabled: bool) -> LangChainTracer | None:
    """Build a request-local tracer without changing process-wide tracing flags."""
    if not enabled:
        return None
    project = os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT") or "fin-research-agent"
    return LangChainTracer(project_name=project)


@app.post("/report")
def create_report(request: ReportRequest):
    if not request.ticker and not request.company_name:
        raise HTTPException(status_code=422, detail="Choose a company before running research.")
    if request.company_name:
        match = next((row for row in _get_company_directory() if row["name"].casefold() == request.company_name.casefold()), None)
        if not match:
            raise HTTPException(status_code=422, detail="Select a company from the search results.")
        ticker = validate_ticker(request.ticker or match["ticker"])
        if ticker != match["ticker"]:
            raise HTTPException(status_code=422, detail="Company name and ticker do not match.")
        company_name = match["name"]
    else:
        ticker = validate_ticker(request.ticker or "")
        company_name = ticker
    logger.info("Starting synchronous report generation for %s", ticker)

    if request.judge_mode == "finetuned":
        raise HTTPException(status_code=422, detail="The fine-tuned Judge requires the optional CUDA/Unsloth setup; use judge_mode='api' unless it is installed.")

    try:
        if request.langsmith_tracing and not langsmith_api_key_configured():
            raise HTTPException(status_code=422, detail="LangSmith tracing is enabled, but no LangSmith API key is configured. Add LANGSMITH_API_KEY to .env and restart the app.")
        initial_state = {
            "ticker": ticker,
            "company_name": company_name,
            "question": request.question,
            "current_query": request.question,
            "judge_mode": request.judge_mode,
            "search_mode": request.search_mode,
            "retrieval_mode": request.retrieval_mode,
            "langsmith_tracing": request.langsmith_tracing,
        }
        tracer = create_langsmith_tracer(request.langsmith_tracing)
        config = {"callbacks": [tracer]} if tracer else None
        result = GRAPH.invoke(initial_state, config=config) if config else GRAPH.invoke(initial_state)
        if tracer:
            try:
                result["langsmith_trace_url"] = tracer.get_run_url()
            except Exception:
                logger.debug("Could not create LangSmith trace URL", exc_info=True)
        save_report(result)
        logger.info("Report saved successfully for %s", ticker)
        return build_ui_payload(result)

    except HTTPException:
        raise

    except openai.APITimeoutError as e:
        logger.exception("AI provider timeout generating report for %s: %s", ticker, e)
        raise HTTPException(
            status_code=504,
            detail="The AI research service timed out. Please try again.",
        ) from e

    except (openai.APIError, RuntimeError) as e:
        logger.exception("Pipeline upstream error generating report for %s: %s", ticker, e)
        raise HTTPException(
            status_code=502,
            detail="Upstream AI provider error occurred while generating report. Please try again.",
        ) from e

    except Exception as e:
        logger.exception("Unexpected error generating report for %s: %s", ticker, e)
        raise HTTPException(
            status_code=500,
            detail="An unexpected internal error occurred.",
        ) from e


@app.get("/report/stream")
def report_stream(
    ticker: str | None = None,
    company_name: str | None = None,
    question: str = Query(..., min_length=1, max_length=500),
    judge_mode: Literal["api", "finetuned"] = "api",
    search_mode: Literal["dense", "bm25", "hybrid"] = "hybrid",
    retrieval_mode: Literal["fixed", "adaptive"] = "fixed",
    langsmith_tracing: bool = False,
):
    if not ticker and not company_name:
        raise HTTPException(status_code=422, detail="Choose a company before running research.")
    if company_name:
        match = next((row for row in _get_company_directory() if row["name"].casefold() == company_name.casefold()), None)
        if not match:
            raise HTTPException(status_code=422, detail="Select a company from the search results.")
        validated_ticker = validate_ticker(ticker or match["ticker"])
        if validated_ticker != match["ticker"]:
            raise HTTPException(status_code=422, detail="Company name and ticker do not match.")
        resolved_company_name = match["name"]
    else:
        validated_ticker = validate_ticker(ticker or "")
        resolved_company_name = validated_ticker
    if judge_mode == "finetuned":
        raise HTTPException(status_code=422, detail="The fine-tuned Judge requires the optional CUDA/Unsloth setup; use judge_mode='api' unless it is installed.")

    def event_generator():
        logger.info("Starting streamed report generation for %s", validated_ticker)
        yield f"event: stage\ndata: {json.dumps({'stage': 'data', 'message': 'Fetching SEC filing & market data...'})}\n\n"

        initial_state = {
            "ticker": validated_ticker,
            "company_name": resolved_company_name,
            "question": question,
            "current_query": question,
            "judge_mode": judge_mode,
            "search_mode": search_mode,
            "retrieval_mode": retrieval_mode,
            "langsmith_tracing": langsmith_tracing,
        }

        try:
            if langsmith_tracing and not langsmith_api_key_configured():
                yield f"event: error\ndata: {json.dumps({'message': 'LangSmith tracing is on, but no LangSmith API key is configured. Add LANGSMITH_API_KEY to .env and restart the app.'})}\n\n"
                return
            final_state = dict(initial_state)
            tracer = create_langsmith_tracer(langsmith_tracing)
            config = {"callbacks": [tracer]} if tracer else None
            stream = GRAPH.stream(initial_state, config=config) if config else GRAPH.stream(initial_state)
            for chunk in stream:
                for node_name, node_output in chunk.items():
                    if isinstance(node_output, dict):
                        final_state.update(node_output)
                    yield f"event: stage\ndata: {json.dumps({'stage': node_name, 'message': f'Completed {node_name}'})}\n\n"
            if tracer:
                try:
                    final_state["langsmith_trace_url"] = tracer.get_run_url()
                except Exception:
                    logger.debug("Could not create LangSmith trace URL", exc_info=True)

            save_report(final_state)
            logger.info("Streamed report saved to database for %s", validated_ticker)

            ui_payload = build_ui_payload(final_state)
            yield f"event: complete\ndata: {json.dumps(ui_payload)}\n\n"

        except Exception as e:
            logger.exception("Streaming error occurred for %s: %s", validated_ticker, e)
            yield f"event: error\ndata: {json.dumps({'message': 'An error occurred while generating the research report. Please try again.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/reports")
def list_reports():
    return [report_payload(report) for report in get_reports()]


@app.get("/reports/{report_id}")
def get_one_report(report_id: int):
    report = get_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report_payload(report)


@app.get("/health")
def health_check():
    db_ok = check_db_connection()
    if not db_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": False},
        )
    return {"status": "ok", "database": db_ok}


# Mount frontend static files for serving UI at "/"
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
