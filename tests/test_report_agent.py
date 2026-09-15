from agents.report_agent import report_agent_node

def test_report_agent_all_fields_present():
    state = {
        "ticker": "AAPL",
        "price_data": {"current_price": 227.5, "fifty_two_week_high": 260.1, "fifty_two_week_low": 164.08},
        "fundamentals": {"pe_ratio": 30, "market_cap": "3.5T"},
        "report_draft": {"bull_points": ["Strong iPhone sales"], "bear_points": ["China risk"], "summary": "Mixed outlook."},
        "judge_score": {"overall": 8, "grounding": 8, "completeness": 7, "clarity": 9, "flagged_issues": []},
    }
    result = report_agent_node(state)
    report = result["final_report"]

    assert "AAPL" in report
    assert "227.5" in report
    assert "Strong iPhone sales" in report
    assert "Overall Score: 8/10" in report


def test_report_agent_missing_fields_does_not_crash():
    """Recreates the Day 18 bug scenario: partial/missing 52-week high/low keys."""
    state = {
        "ticker": "GPRO",
        "price_data": {},          # no fifty_two_week_high/low at all
        "fundamentals": {},
        "report_draft": {},        # no bull/bear/summary at all
        "judge_score": {},         # no scores at all
    }
    result = report_agent_node(state)
    report = result["final_report"]

    assert "GPRO" in report
    assert "N/A" in report
    assert "None identified" in report
    assert "No summary generated." in report