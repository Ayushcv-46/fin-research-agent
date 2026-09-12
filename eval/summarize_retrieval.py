import json
from pathlib import Path

RESULTS_PATH = Path("results/retrieval_comparison.json")

def compute_summary():
    with open(RESULTS_PATH) as f:
        data = json.load(f)

    entries = data.get("results", [])

    buckets = {"fixed": [], "adaptive": []}
    for e in entries:
        mode = e.get("mode")
        if mode in buckets:
            buckets[mode].append(e)

    summary = {}
    for mode, rows in buckets.items():
        valid = [r for r in rows if r.get("faithfulness") is not None]
        retry_eligible = [r for r in rows if r.get("retry_count") is not None]

        avg_faith = (
            sum(r["faithfulness"] for r in valid) / len(valid) if valid else None
        )
        avg_rel = (
            sum(r["answer_relevancy"] for r in valid) / len(valid) if valid else None
        )
        avg_retries = (
            sum(r["retry_count"] for r in retry_eligible) / len(retry_eligible)
            if retry_eligible else None
        )
        retry_rate = (
            sum(1 for r in retry_eligible if r["retry_count"] > 0) / len(retry_eligible)
            if retry_eligible else None
        )

        summary[mode] = {
            "tickers_attempted": len(rows),
            "tickers_scored": len(valid),
            "avg_faithfulness": round(avg_faith, 4) if avg_faith is not None else None,
            "avg_answer_relevancy": round(avg_rel, 4) if avg_rel is not None else None,
            "avg_retry_count": round(avg_retries, 4) if avg_retries is not None else None,
            "retry_rate_pct": round(retry_rate * 100, 2) if retry_rate is not None else None,
        }

    data["summary"] = summary
    with open(RESULTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print("\n=== Retrieval Experiment Summary ===")
    for mode, stats in summary.items():
        print(f"\n[{mode.upper()}]")
        for k, v in stats.items():
            print(f"  {k}: {v}")

if __name__ == "__main__":
    compute_summary()