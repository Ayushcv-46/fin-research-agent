from unittest.mock import patch, MagicMock
from agents.analyst_agent import analyst_agent_node

def _mock_llm_response(text):
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


def test_analyst_empty_chunks_skips_llm_entirely():
    with patch("agents.analyst_agent.llm") as mock_llm:
        state = {"retrieved_chunks": [], "fundamentals": {}}
        result = analyst_agent_node(state)

        mock_llm.invoke.assert_not_called()
        assert result["report_draft"]["summary"] == "Insufficient filing data retrieved to generate analysis."


def test_analyst_llm_failure_falls_back_gracefully():
    with patch("agents.analyst_agent.llm") as mock_llm:
        mock_llm.invoke.side_effect = Exception("LLM down")

        state = {
            "retrieved_chunks": [{"text": "some chunk", "section": "Item 7.", "distance": 0.1}],
            "fundamentals": {},
        }
        result = analyst_agent_node(state)

        assert "Analyst generation failed" in result["report_draft"]["summary"]
        assert result["report_draft"]["bull_points"] == []
        assert result["report_draft"]["bear_points"] == []