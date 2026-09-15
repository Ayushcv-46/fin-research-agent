import sys
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.data_agent import data_agent_node

def test_valid_ticker():
    state = {"ticker": "AAPL"}
    result = data_agent_node(state)
    assert "error" not in result
    assert result["price_data"] is not None
    assert result["filing_text"] is not None
    print("OK: valid ticker test passed")


def test_invalid_ticker():
    state = {"ticker": "ZZZZZNOTREAL"}
    result = data_agent_node(state)
    assert "error" in result
    print("OK: invalid ticker test passed")


def test_missing_fundamentals():
    # pick a small/thinly-covered ticker known to have sparse yfinance data
    state = {"ticker": "GPRO"}
    result = data_agent_node(state)
    if "error" in result:
        print("ERROR IN RESULT:", result["error"])
    assert "error" not in result
    # shouldn't crash even if some fundamentals fields are None
    print("OK: missing fundamentals test passed:", result["fundamentals"])

def test_data_agent_valid_ticker_mocked():
    with patch("agents.data_agent.get_cached", return_value=None), \
         patch("agents.data_agent.set_cached"), \
         patch("agents.data_agent.get_price_snapshot", return_value={"price": 227.5}), \
         patch("agents.data_agent.get_fundamentals", return_value={"pe_ratio": 30}), \
         patch("agents.data_agent.get_cik", return_value="0000320193"), \
         patch("agents.data_agent.get_latest_10k", return_value="<html>raw</html>"), \
         patch("agents.data_agent.clean_filing_text", return_value="cleaned filing text"):

        state = {"ticker": "AAPL"}
        result = data_agent_node(state)

        assert "error" not in result
        assert result["price_data"] == {"price": 227.5}
        assert result["filing_text"] == "cleaned filing text"


def test_data_agent_market_fetch_failure():
    with patch("agents.data_agent.get_cached", return_value=None), \
         patch("agents.data_agent.get_price_snapshot", side_effect=Exception("API down")):

        state = {"ticker": "ZZZZZNOTREAL"}
        result = data_agent_node(state)

        assert "error" in result
if __name__ == "__main__":
    test_valid_ticker()
    test_invalid_ticker()
    test_missing_fundamentals()