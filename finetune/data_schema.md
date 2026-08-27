# Fine-Tuning Data Schema — Judge Distillation

## Purpose
Training data to distill the baseline API Judge (gpt-oss-20b via NVIDIA NIM)
into a local LoRA-fine-tuned Qwen2.5-3B model. Alpaca-style instruction
tuning format, as expected by Unsloth.

## Format (one JSON object per line in .jsonl)

```json
{
  "instruction": "<fixed rubric text, identical in every row>",
  "input": "<report draft + cited chunks for this example>",
  "output": "<JSON judge score + flagged_issues for this example>"
}
```

## instruction (fixed, identical every row)
You are a financial report quality judge. Score the following analyst
report using this rubric. Each criterion is scored 1-10. Overall score is
the average of the three, unless one criterion scores 1-3, in which case
overall should not exceed 5.

1. GROUNDING — Does every claim trace back to explicit language in its
cited chunk (not implied, not adjacent, not a reasonable inference)?
1-3: Claims reference chunks that don't support them, wrong-section
citations, or fabricated/garbled facts presented as real.
4-7: Right area but overstates, adds unstated framing, or blurs a risk
into a positive without contradicting the source.
8-10: Every claim directly traceable to explicit chunk language.

2. COMPLETENESS — Does the report cover what actually matters in the
filing, without padding or omitting a major risk/strength?
1-3: Missing an obviously major risk/opportunity, or generic boilerplate
points.
4-7: Real substance but thin, or one boilerplate point mixed in.
8-10: Every major theme present in the chunks is represented, no filler.

3. CLARITY — Is it organized, unambiguous, and readable on first pass?
1-3: Rambling, contradictory, unclear claim-to-citation mapping.
4-7: Readable but clunky or ambiguous mapping.
8-10: Clean and immediately understandable.

Return JSON: {"grounding": int, "completeness": int, "clarity": int,
"overall": int, "flagged_issues": [str]}

## input
Built by REUSING `agents/prompts/judge_prompt.py`'s existing report+chunk
assembly logic (not a separate formatter) — guarantees training input
matches production input exactly. Contains:
- The report draft (bull_points, bear_points, summary)
- Each cited chunk's text, labeled with its section (e.g. "Item 7", or
  "Item General" for fallback-chunked filings)

## output
Mirrors the live `JudgeScore` Pydantic model exactly:
```json
{"grounding": int, "completeness": int, "clarity": int, "overall": int, "flagged_issues": [short strings]}
```
`flagged_issues` kept as SHORT bullet-style strings (not one long sentence)
— easier for a 3B model to learn to reproduce reliably, and matches the
existing Pydantic schema so no reparsing logic is needed in Day 30.

## Known limitation (documented, not fixed here)
Training labels are the baseline Judge's raw output, including its known
overconfidence bias on grounding (Day 22 finding: Judge grounding avg 7-10
vs. RAGAS faithfulness avg 0.691). The fine-tuned model is expected to
inherit this bias, not correct it. This is intentional — the research
question is "can a small model match the API Judge cheaply," not "is the
API Judge correct." To be stated explicitly in Day 41's Limitations section.