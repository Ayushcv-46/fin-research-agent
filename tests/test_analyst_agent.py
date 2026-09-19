import pytest
from unittest.mock import patch, MagicMock
from agents.analyst_agent import analyst_agent_node


def _mock_llm_response(text: str):
    resp = MagicMock()
    resp.content = text
    return resp


def test_analyst_valid_response():
    good_json = '''{"bull_points": ["Strong margins (Section: Item 7.)"],
                     "bear_points": [], "summary": "Neutral outlook.",
                     "citations": ["Item 7."]}'''
    with patch("agents.analyst_agent.llm") as mock_llm:
        mock_llm.invoke.return_value = _mock_llm_response(good_json)

        state = {
            "retrieved_chunks": [{"text": "some chunk", "section": "Item 7.", "distance": 0.1}],
            "fundamentals": {},
        }
        result = analyst_agent_node(state)

        assert result["report_draft"]["summary"] == "Neutral outlook."
        assert len(result["report_draft"]["bull_points"]) == 1


def test_analyst_fenced_response():
    fenced_json = """```json
    {
      "bull_points": ["Solid revenue growth (Section: Item 7.)"],
      "bear_points": ["FX headwinds (Section: Item 1A.)"],
      "summary": "Balanced risk-reward profile.",
      "citations": ["Item 7.", "Item 1A."]
    }
    ```"""
    with patch("agents.analyst_agent.llm") as mock_llm:
        mock_llm.invoke.return_value = _mock_llm_response(fenced_json)

        state = {
            "retrieved_chunks": [{"text": "some chunk", "section": "Item 7.", "distance": 0.1}],
            "fundamentals": {},
        }
        result = analyst_agent_node(state)

        assert result["report_draft"]["summary"] == "Balanced risk-reward profile."
        assert len(result["report_draft"]["bull_points"]) == 1
        assert len(result["report_draft"]["bear_points"]) == 1


def test_analyst_empty_chunks_skips_llm_entirely():
    with patch("agents.analyst_agent.llm") as mock_llm:
        state = {"retrieved_chunks": [], "fundamentals": {}}
        result = analyst_agent_node(state)

        mock_llm.invoke.assert_not_called()
        assert (
            result["report_draft"]["summary"]
            == "Insufficient filing data retrieved to generate analysis."
        )


def test_analyst_llm_failure_raises():
    with patch("agents.analyst_agent.llm") as mock_llm:
        mock_llm.invoke.side_effect = Exception("LLM down")

        state = {
            "retrieved_chunks": [{"text": "some chunk", "section": "Item 7.", "distance": 0.1}],
            "fundamentals": {},
        }
        with pytest.raises(Exception) as exc_info:
            analyst_agent_node(state)

        assert "LLM down" in str(exc_info.value)


def test_analyst_malformed_json_retries_and_raises():
    with patch("agents.analyst_agent.llm") as mock_llm:
        mock_llm.invoke.return_value = _mock_llm_response("Not JSON at all")

        state = {
            "retrieved_chunks": [{"text": "some chunk", "section": "Item 7.", "distance": 0.1}],
            "fundamentals": {},
        }
        with pytest.raises(RuntimeError) as exc_info:
            analyst_agent_node(state)

        assert "Failed to obtain valid JSON" in str(exc_info.value)
        assert mock_llm.invoke.call_count == 2