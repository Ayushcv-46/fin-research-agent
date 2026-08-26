# tests/e2e_test_run.py

import os
import json
import traceback
from datetime import datetime
from agents.graph import build_graph

TEST_TICKERS = [
    "AAPL", "JPM", "XOM", "UNH", "GOOGL",
    "MSFT", "WMT", "BA", "F", "PLTR",
]

OUTPUT_DIR = "outputs/day19"


def run_single_test(graph, ticker: str) -> dict:
    """Runs the full pipeline for one ticker, catches any crash instead of killing the loop."""
    question = f"How is {ticker}'s growth outlook?"
    try:
        result = graph.invoke({
            "ticker": ticker,
            "question": question,
            "current_query": question,
        })
        return {
            "ticker": ticker,
            "status": "success",
            "final_report": result.get("final_report", ""),
            "judge_score": result.get("judge_score", {}),
            "retry_count": result.get("retry_count", 0),
            "error": None,
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "status": "crash",
            "final_report": None,
            "judge_score": None,
            "retry_count": None,
            "error": f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
        }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    graph = build_graph()

    summary_log = []

    for ticker in TEST_TICKERS:
        print(f"\n=== Running {ticker} ===")
        outcome = run_single_test(graph, ticker)

        # Save individual report to its own file
        filepath = os.path.join(OUTPUT_DIR, f"{ticker}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            if outcome["status"] == "success":
                f.write(outcome["final_report"])
                f.write(f"\n\n---\nRetry count: {outcome['retry_count']}\n")
            else:
                f.write(f"# CRASHED: {ticker}\n\n{outcome['error']}")

        print(f"  status: {outcome['status']}")
        if outcome["status"] == "success":
            print(f"  judge overall: {outcome['judge_score'].get('overall', 'N/A')}")
        else:
            print(f"  ERROR: {outcome['error'][:200]}")

        summary_log.append({
            "ticker": outcome["ticker"],
            "status": outcome["status"],
            "judge_overall": (outcome["judge_score"] or {}).get("overall") if outcome["status"] == "success" else None,
            "retry_count": outcome["retry_count"],
            "error": outcome["error"],
        })

    # Save one combined summary JSON for quick scanning
    summary_path = os.path.join(OUTPUT_DIR, "_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_at": datetime.now().isoformat(),
            "results": summary_log,
        }, f, indent=2)

    print(f"\n=== Done. {len(TEST_TICKERS)} tickers tested. Summary: {summary_path} ===")


if __name__ == "__main__":
    main()