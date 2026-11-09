def report_agent_node(state: dict) -> dict:
    price_data = state.get("price_data") or {}
    fundamentals = state.get("fundamentals") or {}
    report_draft = state.get("report_draft") or {}
    retrieved_chunks = state.get("retrieved_chunks") or []
    filing = state.get("filing_metadata") or {}

    overview = report_draft.get("overview") or report_draft.get("summary") or "The available filing evidence was not enough to provide a clear overview."
    strengths = report_draft.get("bull_points") or []
    risks = report_draft.get("bear_points") or []
    summary = report_draft.get("summary") or "No clear takeaway could be generated from the available evidence."

    sources = "\n".join(
        f"<li><strong>{chunk.get('section', 'Unknown section')}</strong> — "
        f"{chunk.get('text', '')[:700]}{'…' if len(chunk.get('text', '')) > 700 else ''}</li>"
        for chunk in retrieved_chunks
    ) or "<li>No filing passages were retrieved for this question.</li>"

    report = f"""## In brief
{overview}

## Key strengths
{chr(10).join(f"- {item}" for item in strengths) if strengths else "- No clearly supported strengths were found in the passages retrieved."}

## Risks to know
{chr(10).join(f"- {item}" for item in risks) if risks else "- No clearly supported risks were found in the passages retrieved."}

## Takeaway
{summary}

## Market Snapshot
- **Share price:** {price_data.get('current_price', 'Not available')}
- **52-week range:** {price_data.get('fifty_two_week_low', 'Not available')} – {price_data.get('fifty_two_week_high', 'Not available')}
- **P/E ratio:** {fundamentals.get('pe_ratio', 'Not available')}
- **Market capitalization:** {fundamentals.get('market_cap', 'Not available')}
- **Market data fetched:** {state.get('market_data_as_of', 'Unknown')}

## Sources
- **Annual report filed:** {filing.get('filing_date', 'Unknown')}
- **Financial year ended:** {filing.get('report_date', 'Unknown')}
- **SEC filing:** {filing.get('url', 'Unavailable')}

<details>
<summary>View supporting passages</summary>
<ul>
{sources}
</ul>
</details>
"""


    warnings = state.get("data_warnings") or []
    if warnings:
        report += "\n## Data availability\n" + "\n".join(f"- {warning}" for warning in warnings)
    report += "\n> Educational information only. This is not personalized financial advice or a buy/sell recommendation. Check important details against the linked filing.\n"
    return {"final_report": report}
