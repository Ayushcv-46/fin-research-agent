from unittest.mock import patch, MagicMock
from agents.judge_agent import judge_agent_node, JudgeScore

def _mock_llm_response(text):
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


def test_judge_api_mode_llm_failure_returns_sentinel():
    with patch("agents.judge_agent.llm") as mock_llm, \
         patch("agents.judge_agent.JUDGE_MODE", "api"):
        mock_llm.invoke.side_effect = Exception("API timeout")

        state = {"report_draft": {"summary": "x"}, "retrieved_chunks": []}
        result = judge_agent_node(state)

        assert result["judge_score"]["overall"] == -1
        assert result["judge_score"]["grounding"] == -1
        assert "failed" in result["judge_score"]["flagged_issues"][0].lower()


def test_judge_api_mode_malformed_json_returns_sentinel():
    with patch("agents.judge_agent.llm") as mock_llm, \
         patch("agents.judge_agent.JUDGE_MODE", "api"):
        mock_llm.invoke.return_value = _mock_llm_response("I refuse to output JSON today.")

        state = {"report_draft": {"summary": "x"}, "retrieved_chunks": []}
        result = judge_agent_node(state)

        assert result["judge_score"] == {
            "grounding": -1, "completeness": -1, "clarity": -1, "overall": -1,
            "flagged_issues": ["Judge evaluation failed — LLM call error, this score is not real"],
        }


def test_judge_skip_flag_bypasses_llm():
    with patch.dict("os.environ", {"SKIP_JUDGE": "true"}):
        state = {"report_draft": {}, "retrieved_chunks": []}
        result = judge_agent_node(state)
        assert result["judge_score"]["overall"] == 0
        assert result["judge_score"]["flagged_issues"] == ["[skipped during experiment]"]