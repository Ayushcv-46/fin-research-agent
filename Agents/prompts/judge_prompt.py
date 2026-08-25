def build_judge_prompt(report_draft: dict, retrieved_chunks: list[dict]) -> str:
    chunks_text = "\n\n".join(
        f"[Section: {c.get('section', 'Unknown')}]\n{c.get('text', '')}"
        for c in retrieved_chunks
    )

    return f"""You are a strict financial research reviewer.

RUBRIC:
- Grounding (1-10): Does every claim trace back to a chunk below? Check citations against actual chunk content, not just plausibility.
- Completeness (1-10): Are major risks/opportunities present in the source chunks reflected in the report? Flag missing coverage.
- Clarity (1-10): Is the report well-organized, unambiguous, and free of filler/placeholder text.

SOURCE CHUNKS:
{chunks_text if chunks_text else "(no chunks retrieved)"}

REPORT TO REVIEW:
Bull points: {report_draft.get('bull_points', [])}
Bear points: {report_draft.get('bear_points', [])}
Summary: {report_draft.get('summary', '')}
Citations: {report_draft.get('citations', [])}

INSTRUCTIONS:
1. First, go point by point (each bull point, bear point) and check it against the source chunks. For each one, note in your reasoning whether it is grounded, ungrounded (wrong section), or filler text.
2. Build the flagged_issues list from that point-by-point check — one entry per specific problem found.
3. YOUR NUMERIC SCORES MUST MATCH flagged_issues. Specifically:
   - If more than half the claims are ungrounded or filler text, grounding MUST be 3 or lower.
   - If any claim is filler text with no real content, completeness MUST be 5 or lower.
   - overall MUST NOT exceed the lowest of grounding, completeness, and clarity by more than 1 point.
   - A high score (8+) on any criterion requires zero flagged_issues related to that criterion.
4. Do not soften scores out of politeness. A report with many flagged issues must receive low scores that reflect that.

Score each criterion 1-10, give an overall 1-10 score, and list specific flagged_issues as short, concrete strings (e.g. "Bull point 2 cites Item 7 but that section covers supply chain, not growth")."""