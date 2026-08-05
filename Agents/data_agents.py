import os
import sys

# Ensure project root is in sys.path when executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import TypedDict, Optional
# pyrefly: ignore [missing-import]
from data.market_data import get_price_snapshot, get_fundamentals
# pyrefly: ignore [missing-import]
from data.edgar_fetcher import get_cik, get_latest_10k, clean_filing_text


class GraphState(TypedDict):
    ticker: str
    price_data: Optional[dict]
    fundamentals: Optional[dict]
    filing_text: Optional[str]
    retrieved_chunks: Optional[list]
    report_draft: Optional[dict]
    judge_score: Optional[dict]
    final_report: Optional[str]
    error: Optional[str]


def data_agent_node(state: GraphState) -> dict:
    ticker = state.get("ticker")

    if not ticker:
        return {"error": "No ticker provided in state."}

    price_data = get_price_snapshot(ticker)
    fundamentals = get_fundamentals(ticker)

    if price_data.get("error") and fundamentals.get("error"):
        return {
            "price_data": price_data,
            "fundamentals": fundamentals,
            "filing_text": None,
            "error": f"Could not fetch market data for '{ticker}'.",
        }

    filing_text = None
    filing_error = None

    try:
        cik = get_cik(ticker)
        if not cik:
            filing_error = f"No CIK found for ticker '{ticker}'."
        else:
            raw_html = get_latest_10k(cik)
            filing_text = clean_filing_text(raw_html)
    except Exception as e:
        filing_error = str(e)

    return {
        "price_data": price_data,
        "fundamentals": fundamentals,
        "filing_text": filing_text,
        "error": filing_error,
    }


if __name__ == "__main__":
    test_state: GraphState = {"ticker": "IBM"}
    result = data_agent_node(test_state)

    print("Price data:", result.get("price_data"))
    print("Fundamentals:", result.get("fundamentals"))
    print("Filing text (first 300 chars):", (result.get("filing_text") or "")[:300])
    print("Error:", result.get("error"))