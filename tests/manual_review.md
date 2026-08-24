# Day 15 — Manual Review: Analyst Agent Across 5 Companies

Tested tickers: JPM, WMT, XOM, UNH, AAPL (financials, retail, energy, healthcare, tech)

## JPM — Clean
Report correctly pulled from Item 15 (risk governance / VaR / cybersecurity).
Bull and bear points are distinct and grounded. No issues.

## WMT — Weak bull case (padding via repetition)
All 3 bull_points paraphrase the same single sentence about the omnichannel
strategy ("may allow... may be successful... may be a competitive advantage").
Not fabricated, but not genuinely 3 distinct points either — retrieval only
surfaced Item 1A/Item 1, which is risk-framed, so there's minimal real positive
material to draw 3 points from.
Status: OPEN — retrieval-side fix needed (see below), not a prompt bug.

## XOM — BLOCKER: ingestion failure
`[retriever_agent] Failed to obtain filing_text for ingestion for XOM` — repeated
3x, collection stayed empty, report_draft came back fully empty.
Root cause not yet identified — needs standalone testing of get_cik("XOM") and
get_latest_10k(cik) before Day 19's 10-company stress test.
Status: OPEN.

## UNH — Retrieval picked the wrong section
Both retrieved chunks came from Item 9A (internal controls / governance
boilerplate) instead of Risk Factors or MD&A. Bull and bear points both
describe the same intercompany notes payable fact from opposite framing, and
dollar figures came back blank ("$ billion") from a mangled financial table.
Status: OPEN — needs a check of UNH's section header formatting / why the
"risks and opportunities" query is matching governance text.

## AAPL — Prompt padding: FIXED, but surfaced a grounding issue
Original bug: analyst returned a literal filler bull_point ("No significant
bull case found in the provided sources.") when the source material was
entirely risk-framed (Item 1A only).
Fix applied: analyst_prompt.py instructions changed from "List 2-3" to "List
up to 3... if the chunks support them," rule 7 changed to instruct an empty
list instead of a placeholder sentence, and ReportDraft's Field descriptions
in the Pydantic schema updated to match (the schema description was silently
re-asserting the "2-3 required" instruction even after the prompt text
changed).
Re-test confirms: no more filler text, on AAPL or any other ticker.

New issue surfaced by the same re-test: bull_point 1 claims "the Company
believes that it generally benefits from growth in international trade" —
this is not supported by the retrieved chunk, which only states international
sales are a majority of net sales in a risk-framed context. This is a
faithfulness violation (rule 6 in the prompt exists specifically to prevent
this) that the filler-text bug was masking. Since the model had nothing
genuinely positive to cite, it fabricated an attributed belief instead of
returning fewer points.
Status: OPEN — needs a stricter rule 6 addition (no attributing beliefs/
opinions/intentions to the Company unless explicitly stated in source text).

## Recurring issue identified
When retrieval only surfaces Item 1A (Risk Factors), the Analyst Agent has no
genuine bullish material to cite. Making point-count "up to 3" instead of
mandatory stopped the model from inventing filler text, but it still finds
other ways to fill the count when a real ceiling isn't enforced: either
near-duplicate rewording (WMT) or fabricated attribution (AAPL). The real fix
is retrieval-side — pull Item 7 (MD&A) alongside Item 1A for bull-case
queries, same fix already applied for a different symptom of this in Day 13.

## Status summary
- Fixed this session: AAPL literal filler-text bug
- Confirmed clean: JPM
- Open, retrieval-side: WMT (weak/repetitive bull case), UNH (wrong section
  entirely), AAPL (fabricated attribution)
- Open, blocker: XOM (ingestion failure)