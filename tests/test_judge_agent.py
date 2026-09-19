from unittest.mock import patch, MagicMock
from agents.judge_agent import judge_agent_node



def _mock_llm_response(text: str):
    resp = MagicMock()
    resp.content = text
    return resp


def test_judge_api_mode_valid_response():
    good_json = '{"grounding": 8, "completeness": 7, "clarity": 9, "overall": 8, "flagged_issues": []}'
    with patch("agents.judge_agent.llm") as mock_llm, \
         patch("agents.judge_agent.JUDGE_MODE", "api"):
        mock_llm.invoke.return_value = _mock_llm_response(good_json)

        state = {"report_draft": {"summary": "x"}, "retrieved_chunks": []}
        result = judge_agent_node(state)

        assert result["judge_score"]["overall"] == 8
        assert result["judge_score"]["flagged_issues"] == []


def test_judge_api_mode_fenced_json_response():
    fenced_json = """```json
    {
      "grounding": 9,
      "completeness": 8,
      "clarity": 9,
      "overall": 9,
      "flagged_issues": []
    }
    ```"""
    with patch("agents.judge_agent.llm") as mock_llm, \
         patch("agents.judge_agent.JUDGE_MODE", "api"):
        mock_llm.invoke.return_value = _mock_llm_response(fenced_json)

        state = {"report_draft": {"summary": "x"}, "retrieved_chunks": []}
        result = judge_agent_node(state)

        assert result["judge_score"]["overall"] == 9
        assert result["judge_score"]["grounding"] == 9


def test_judge_api_mode_llm_failure_returns_none():
    with patch("agents.judge_agent.llm") as mock_llm, \
         patch("agents.judge_agent.JUDGE_MODE", "api"):
        mock_llm.invoke.side_effect = Exception("API timeout")

        state = {"report_draft": {"summary": "x"}, "retrieved_chunks": []}
        result = judge_agent_node(state)

        assert result["judge_score"] is None


def test_judge_api_mode_malformed_json_returns_none():
    with patch("agents.judge_agent.llm") as mock_llm, \
         patch("agents.judge_agent.JUDGE_MODE", "api"):
        mock_llm.invoke.return_value = _mock_llm_response("I refuse to output JSON today.")

        state = {"report_draft": {"summary": "x"}, "retrieved_chunks": []}
        result = judge_agent_node(state)

        assert result["judge_score"] is None



def test_judge_skip_flag_bypasses_llm():
    with patch.dict("os.environ", {"SKIP_JUDGE": "true"}):
        state = {"report_draft": {}, "retrieved_chunks": []}
        result = judge_agent_node(state)
        assert result["judge_score"]["overall"] == 0
        assert result["judge_score"]["flagged_issues"] == ["[skipped during experiment]"]