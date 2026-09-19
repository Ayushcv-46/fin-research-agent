def report_agent_node(state: dict) -> dict:
    ticker = state.get("ticker", "UNKNOWN")
    price_data = state.get("price_data", {})
    fundamentals = state.get("fundamentals", {})
    report_draft = state.get("report_draft", {})
    judge_score = state.get("judge_score", {})

    bull_points = report_draft.get("bull_points", [])
    bear_points = report_draft.get("bear_points", [])
    summary = report_draft.get("summary", "")

    final_report = f"""# Financial Research Report: {ticker}

## Market Snapshot
- Price: {price_data.get('current_price', 'N/A')}
- 52W High/Low: {price_data.get('fifty_two_week_high', 'N/A')} / {price_data.get('fifty_two_week_low', 'N/A')}
- P/E: {fundamentals.get('pe_ratio', 'N/A')}
- Market Cap: {fundamentals.get('market_cap', 'N/A')}

## Bull Case
{chr(10).join(f"- {p}" for p in bull_points) if bull_points else "- None identified"}

## Bear Case
{chr(10).join(f"- {p}" for p in bear_points) if bear_points else "- None identified"}

## Summary
{summary if summary else "No summary generated."}

---
## Judge Assessment (Transparency Panel)
- Overall Score: {judge_score.get('overall', 'N/A')}/10
- Grounding: {judge_score.get('grounding', 'N/A')}/10 | Completeness: {judge_score.get('completeness', 'N/A')}/10 | Clarity: {judge_score.get('clarity', 'N/A')}/10
- Flagged Issues: {judge_score.get('flagged_issues', []) or 'None'}
"""

    return {"final_report": final_report}