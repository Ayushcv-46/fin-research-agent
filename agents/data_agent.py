import os
import sys
from datetime import datetime, timezone
from typing import TypedDict, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.cache import get_cached, set_cached
from data.market_data import get_price_snapshot, get_fundamentals
from data.edgar_fetcher import get_cik, get_latest_10k, get_latest_10k_record, clean_filing_text


class GraphState(TypedDict, total=False):
    ticker: str
    question: str
    current_query: str
    price_data: Optional[dict]
    fundamentals: Optional[dict]
    filing_text: Optional[str]
    filing_id: str
    filing_metadata: dict
    market_data_as_of: str
    data_warnings: list
    retrieved_chunks: Optional[list]
    report_draft: Optional[dict]
    judge_score: Optional[dict]
    final_report: Optional[str]
    error: Optional[str]


def data_agent_node(state: dict) -> dict:
    ticker = state["ticker"]
    if not state.get("company_name"):
        state["company_name"] = ticker
    warnings = list(state.get("data_warnings", []))

    market_data = get_cached(f"market:{ticker}")
    if market_data is not None and state.get("market_data_as_of"):
        market_data = {**market_data, "as_of": state["market_data_as_of"]}
    if market_data is None:
        try:
            market_data = {
                "price": get_price_snapshot(ticker),
                "fundamentals": get_fundamentals(ticker),
                "as_of": state.get("market_data_as_of") or datetime.now(timezone.utc).isoformat(),
            }
            set_cached(f"market:{ticker}", market_data)
        except Exception as exc:
            warnings.append(f"Market data unavailable: {exc}")
    else:
        market_data.setdefault("as_of", "unknown (legacy cache entry)")

    if market_data:
        state["price_data"] = market_data.get("price")
        state["fundamentals"] = market_data.get("fundamentals")
        state["market_data_as_of"] = market_data.get("as_of")

    # Fetch filing metadata first so the content cache and Chroma collection are
    # keyed by accession rather than ticker. This prevents stale filings being mixed.
    try:
        cik = get_cik(ticker)
        try:
            record = get_latest_10k_record(cik)
            filing_id = record["accession_number"]
        except (AttributeError, NotImplementedError, RuntimeError):
            # Compatibility path for existing integrations/tests that stub the
            # original HTML-only fetch function.
            filing_id = "legacy"
            record = {"html": get_latest_10k(cik), "accession_number": "legacy",
                      "filing_date": None, "report_date": None, "form": "10-K", "url": None}
        cache_key = f"filing:{ticker}:{filing_id}"
        cached_filing = get_cached(cache_key)
        if isinstance(cached_filing, dict):
            filing_text = cached_filing["text"]
        else:
            filing_text = clean_filing_text(record["html"])
            set_cached(cache_key, {"text": filing_text})
        state["filing_text"] = filing_text
        state["filing_id"] = filing_id
        state["filing_metadata"] = {k: v for k, v in record.items() if k != "html"}
    except Exception as exc:
        warnings.append(f"SEC filing unavailable: {exc}")
        state["filing_text"] = None

    state["data_warnings"] = warnings
    if warnings and not state.get("price_data") and not state.get("filing_text"):
        state["error"] = f"No research data could be fetched for {ticker}."
    return state
