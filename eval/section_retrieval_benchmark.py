"""Compare dense, BM25, and RRF hybrid retrieval on explicit SEC sections.

Labels are expected Item sections from the question set, not human-labeled
passage relevance judgments. Uses existing local Chroma indexes; no APIs called.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from retrieval.vector_store import query_filing

CASES = [
    ("AAPL", "What products and services does the company sell?", ["Item 1."]),
    ("AAPL", "What are the principal risks facing the business?", ["Item 1A."]),
    ("AAPL", "Discuss management's analysis of revenue and operating results.", ["Item 7."]),
    ("AAPL", "Summarize the audited financial statements.", ["Item 8."]),
    ("MSFT", "What products and services does the company sell?", ["Item 1."]),
    ("MSFT", "What are the principal risks facing the business?", ["Item 1A."]),
    ("MSFT", "Discuss management's analysis of revenue and operating results.", ["Item 7."]),
    ("MSFT", "Summarize the audited financial statements.", ["Item 8."]),
    ("XOM", "Describe the company's operating business and segments.", ["Item 1."]),
    ("XOM", "What are the principal risks facing the business?", ["Item 1A."]),
    ("XOM", "Discuss management's analysis of results and liquidity.", ["Item 7."]),
    ("XOM", "Summarize the audited financial statements.", ["Item 8."]),
    ("GOOGL", "What products and services does the company sell?", ["Item 1."]),
    ("GOOGL", "What are the principal risks facing the business?", ["Item 1A."]),
    ("GOOGL", "Discuss management's analysis of revenue and operating results.", ["Item 7."]),
    ("GOOGL", "Summarize the audited financial statements.", ["Item 8."]),
    ("WMT", "Describe the company's operations and services.", ["Item 1."]),
    ("WMT", "What are the principal risks facing the business?", ["Item 1A."]),
    ("WMT", "Discuss management's analysis of financial results.", ["Item 7."]),
    ("WMT", "Summarize the audited financial statements.", ["Item 8."]),
    ("NVDA", "What products and services does the company sell?", ["Item 1."]),
    ("NVDA", "What are the principal risks facing the business?", ["Item 1A."]),
    ("NVDA", "Discuss management's analysis of revenue and operating results.", ["Item 7."]),
    ("NVDA", "Summarize the audited financial statements.", ["Item 8."]),
]
MODES = ("dense", "bm25", "hybrid")


def _metrics(rows: list[dict]) -> dict:
    if not rows:
        return {"queries": 0, "section_recall_at_5": None, "mrr": None}
    hits, reciprocal_ranks = [], []
    for row in rows:
        expected = set(row["expected_sections"])
        sections = [chunk.get("section") for chunk in row["results"]]
        hits.append(bool(expected.intersection(sections)))
        rank = next((i for i, section in enumerate(sections, start=1) if section in expected), None)
        reciprocal_ranks.append(1 / rank if rank else 0)
    return {"queries": len(rows), "section_recall_at_5": round(sum(hits) / len(hits), 3),
            "mrr": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 3)}


def run(output_path: Path = Path("results/section_retrieval_benchmark.json")) -> dict:
    by_mode = {mode: [] for mode in MODES}
    for ticker, question, expected in CASES:
        for mode in MODES:
            try:
                results = query_filing(ticker, question, top_k=5, search_mode=mode)
                error = None
            except Exception as exc:
                results, error = [], str(exc)
            by_mode[mode].append({"ticker": ticker, "question": question,
                                  "expected_sections": expected,
                                  "retrieved_sections": [r.get("section") for r in results],
                                  "results": results, "error": error})
    summary = {mode: _metrics(rows) for mode, rows in by_mode.items()}
    compact_cases = {mode: [{k: v for k, v in row.items() if k != "results"} for row in rows]
                     for mode, rows in by_mode.items()}
    payload = {"created_at": datetime.now(timezone.utc).isoformat(),
               "label_type": "expected SEC section; not passage-level human relevance judgments",
               "top_k": 5, "summary": summary, "cases": compact_cases}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote {output_path}")
    return payload


if __name__ == "__main__":
    run()
