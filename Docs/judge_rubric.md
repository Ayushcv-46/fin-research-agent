# Judge Rubric — Financial Research Analyst

This rubric is applied identically by the baseline API Judge (Day 17) and,
later, the LoRA fine-tuned Judge (Phase 8) — consistency here is what makes
the fine-tuning distillation task meaningful.

Each criterion is scored 1-10. Overall score is the average of the three,
unless one criterion scores 1-3, in which case overall should not exceed 5
(a severe grounding failure or major omission caps the report regardless of
how clear or complete it otherwise is).

## 1. Grounding
Does every claim trace back to explicit language in its cited chunk — not
implied, not adjacent, not a reasonable-sounding inference, but actually
stated?

Check: for each point, find the cited chunk and ask "if I only had this
chunk, could I write this sentence?" Not "is this a reasonable
extrapolation" — could you point to the actual words.

| Score | Anchor |
|---|---|
| 1-3 | Claims reference chunks that don't support them, citations point to the wrong section, or specific facts/numbers are fabricated or presented as real when the source was garbled/blank |
| 4-7 | Broadly in the right area but overstates, adds unstated framing/attribution (e.g. "the Company believes..." when the source never says that), or blurs a risk statement into a positive without contradicting the source |
| 8-10 | Every claim is directly traceable to explicit language in its cited chunk |

Example failure (AAPL, Day 15): bull_point claimed "the Company believes it
generally benefits from growth in international trade," citing a chunk that
only states international sales are a majority of net sales, in a
risk-framed passage. Score: 4-7 range — not fabricated from nothing, but
adds an unstated belief/attribution.

## 2. Completeness
Does the report cover what actually matters in the retrieved filing text,
without padding with generic boilerplate or omitting an obviously major
risk/strength?

| Score | Anchor |
|---|---|
| 1-3 | Missing an obviously major risk/opportunity present in the chunks; or points are generic boilerplate that could apply to almost any company |
| 4-7 | Covers real substance but thin — fewer genuine points than the source supports, or mixes one boilerplate point in with genuine ones |
| 8-10 | Every major theme actually present in the retrieved chunks is represented, no filler padding the count |

Example failure (XOM, Day 15): bull_point "recognizes the importance of
cybersecurity" is technically traceable (passes Grounding) but is generic
risk-mitigation boilerplate that isn't a real distinguishing strength. Score:
1-3 range on Completeness specifically.

## 3. Clarity
Is it organized, unambiguous, and readable without needing a second pass?

| Score | Anchor |
|---|---|
| 1-3 | Rambling, contradictory, or unclear which claim supports which point |
| 4-7 | Readable but clunky phrasing or ambiguous claim-to-citation mapping |
| 8-10 | Clean, immediately understandable on first read |