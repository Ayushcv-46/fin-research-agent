def report_agent_node(state: dict) -> dict:
    ticker = state.get("ticker", "UNKNOWN")
    price_data = state.get("price_data") or {}
    fundamentals = state.get("fundamentals") or {}
    report_draft = state.get("report_draft") or {}
    retrieved_chunks = state.get("retrieved_chunks") or []

    bull_points = report_draft.get("bull_points", [])
    bear_points = report_draft.get("bear_points", [])
    summary = report_draft.get("summary", "")

    sources_html = "\n".join([f"<li>{chunk}</li>" for chunk in retrieved_chunks])
    if not sources_html:
        sources_html = "<li>No sources available.</li>"

    final_report = f"""## Market Snapshot
- **Price:** {price_data.get('current_price', 'N/A')}
- **52W High/Low:** {price_data.get('fifty_two_week_high', 'N/A')} / {price_data.get('fifty_two_week_low', 'N/A')}
- **P/E:** {fundamentals.get('pe_ratio', 'N/A')}
- **Market Cap:** {fundamentals.get('market_cap', 'N/A')}

## Bull Case
{chr(10).join(f"- {p}" for p in bull_points) if bull_points else "- None identified"}

## Bear Case
{chr(10).join(f"- {p}" for p in bear_points) if bear_points else "- None identified"}

## Summary
{summary if summary else "No summary generated."}

## Sources
<details class="bg-gray-50 p-4 rounded border mt-2 cursor-pointer">
<summary class="font-semibold text-gray-700">View Sources</summary>
<ul class="list-disc pl-5 mt-2 text-gray-600 text-sm space-y-2">
{sources_html}
</ul>
</details>
"""

    return {"final_report": final_report}