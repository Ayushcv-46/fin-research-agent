# eval/baseline_report.py
import json
import os
from datetime import datetime
from agents.graph import build_graph
from eval.ragas_eval import run_ragas_evaluation

TEST_TICKERS = ["AAPL", "JPM", "XOM", "UNH", "GOOGL", "MSFT", "WMT", "BA", "F", "PLTR"]
OUTPUT_DIR = "results"


def run_pipeline_for_ragas(graph, ticker: str) -> dict:
    question = f"How is {ticker}'s growth outlook?"
    try:
        result = graph.invoke({
            "ticker": ticker,
            "question": question,
            "current_query": question,
        })
        return {
            "ticker": ticker,
            "question": question,
            "retrieved_chunks": result.get("retrieved_chunks", []),
            "final_report": result.get("final_report", ""),
            "judge_score": result.get("judge_score", {}),
            "retry_count": result.get("retry_count", 0),
            "status": "success",
        }
    except Exception as e:
        return {"ticker": ticker, "status": "crash", "error": str(e)}


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    graph = build_graph()

    pipeline_results = []
    for ticker in TEST_TICKERS:
        print(f"\n=== Running {ticker} for baseline eval ===")
        r = run_pipeline_for_ragas(graph, ticker)
        pipeline_results.append(r)
        print(f"  status: {r['status']}")

    successful = [r for r in pipeline_results if r["status"] == "success"]
    print(f"\n{len(successful)}/{len(TEST_TICKERS)} succeeded, running RAGAS...")

    ragas_scores = run_ragas_evaluation(successful)

    # per-ticker judge scores + latency notes (cost/latency stubbed for Day 33 later)
    baseline = {
        "run_at": datetime.now().isoformat(),
        "ragas_scores": ragas_scores,
        "per_ticker": [
            {
                "ticker": r["ticker"],
                "status": r["status"],
                "judge_overall": r.get("judge_score", {}).get("overall") if r["status"] == "success" else None,
                "retry_count": r.get("retry_count"),
            }
            for r in pipeline_results
        ],
    }

    with open(os.path.join(OUTPUT_DIR, "baseline.json"), "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2)

    print(f"\n=== Done. results/baseline.json written. RAGAS: {ragas_scores} ===")


if __name__ == "__main__":
    main()