import os
import json
import time
from pathlib import Path
from agents.graph import build_graph
from eval.ragas_eval import run_ragas_evaluation

os.environ["SKIP_JUDGE"] = "true"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

GRAPH = build_graph()

# Removed large-filing tickers: JPM (12.9MB), BAC (12.8MB)
# Kept mid-size filings that completed successfully in first run
TICKERS = [
    "AAPL", "TSLA", "NFLX",        # confirmed working in first run
    "GOOGL", "META", "AMZN",       # mid-size, worth retrying
    "MSFT", "NVDA", "WMT",         # some succeeded, worth retrying
    "PFE", "DIS", "XOM"            # mid-size, retry
]

RESULTS_PATH = Path("results/retrieval_comparison.json")
RESULTS_PATH.parent.mkdir(exist_ok=True)

if RESULTS_PATH.exists():
    with open(RESULTS_PATH) as f:
        data = json.load(f)
else:
    data = {"results": []}

already_done = {
    (r["ticker"], r["mode"]) for r in data["results"]
}

for mode in ["fixed", "adaptive"]:
    os.environ["RETRIEVAL_MODE"] = mode
    print(f"\n=== Running mode: {mode.upper()} ===")

    for ticker in TICKERS:
        if (ticker, mode) in already_done:
            print(f"  Skipping {ticker} ({mode}) — already in results")
            continue

        print(f"  Running {ticker}...")
        entry = {
            "ticker": ticker,
            "mode": mode,
            "faithfulness": None,
            "answer_relevancy": None,
            "retry_count": None
        }

        try:
            state = GRAPH.invoke({
                "ticker": ticker,
                "question": f"What are the main risks and growth opportunities for {ticker}?"
            })

            entry["retry_count"] = state.get("retry_count", 0)

            ragas_scores = run_ragas_evaluation([state])
            if ragas_scores:
                entry["faithfulness"] = ragas_scores.get("faithfulness")
                entry["answer_relevancy"] = ragas_scores.get("answer_relevancy")

        except Exception as e:
            print(f"  ERROR on {ticker} ({mode}): {e}")

        data["results"].append(entry)

        with open(RESULTS_PATH, "w") as f:
            json.dump(data, f, indent=2)

        print(f"  Done {ticker} ({mode}): faithfulness={entry['faithfulness']}, retries={entry['retry_count']}")

        # Cooldown between tickers to avoid hitting API rate limits
        print(f"  Waiting 30s before next ticker...")
        time.sleep(30)

print("\nExperiment complete. Run eval/summarize_retrieval.py to see summary stats.")