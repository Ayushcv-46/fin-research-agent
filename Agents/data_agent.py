import os
import sys

# Ensure project root is in sys.path when executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import TypedDict, Optional
from data.cache import get_cached, set_cached
# pyrefly: ignore [missing-import]
from data.market_data import get_price_snapshot, get_fundamentals
# pyrefly: ignore [missing-import]
from data.edgar_fetcher import get_cik, get_latest_10k, clean_filing_text


class GraphState(TypedDict):
    ticker: str
    question: str
    price_data: Optional[dict]
    fundamentals: Optional[dict]
    filing_text: Optional[str]
    retrieved_chunks: Optional[list]
    report_draft: Optional[dict]
    judge_score: Optional[dict]
    final_report: Optional[str]
    error: Optional[str]


def data_agent_node(state: dict) -> dict:
    ticker = state["ticker"]

    # --- price + fundamentals, cached together under one key ---
    cache_key_market = f"market:{ticker}"
    market_data = get_cached(cache_key_market)

    if market_data is None:
        try:
            price = get_price_snapshot(ticker)
            fundamentals = get_fundamentals(ticker)
            market_data = {"price": price, "fundamentals": fundamentals}
            set_cached(cache_key_market, market_data)
        except Exception as e:
            state["error"] = f"Failed to fetch market data for {ticker}: {e}"
            return state

    state["price_data"] = market_data["price"]
    state["fundamentals"] = market_data["fundamentals"]

    # --- filing text, cached separately ---
    cache_key_filing = f"filing:{ticker}"
    filing_text = get_cached(cache_key_filing)

    if filing_text is None:
        try:
            cik = get_cik(ticker)
            raw_html = get_latest_10k(cik)
            filing_text = clean_filing_text(raw_html)
            set_cached(cache_key_filing, filing_text)
        except Exception as e:
            state["error"] = f"Failed to fetch filing for {ticker}: {e}"
            return state

    state["filing_text"] = filing_text
    return state


if __name__ == "__main__":
    test_state: GraphState = {"ticker": "IBM"}
    result = data_agent_node(test_state)

    print("Price data:", result.get("price_data"))
    print("Fundamentals:", result.get("fundamentals"))
    print("Filing text (first 300 chars):", (result.get("filing_text") or "")[:300])
    print("Error:", result.get("error"))