import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.data_agents import data_agent_node

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


if __name__ == "__main__":
    test_valid_ticker()
    test_invalid_ticker()
    test_missing_fundamentals()