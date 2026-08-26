# Baseline Metrics Report — Day 22

**Run date:** (fill in from results/baseline.json `run_at`)
**Test set:** 10 tickers — AAPL, JPM, XOM, UNH, GOOGL, MSFT, WMT, BA, F, PLTR
**Question template:** "How is {ticker}'s growth outlook?"

## RAGAS Scores (averaged across 10 companies)

| Metric | Score |
|---|---|
| Faithfulness | 0.691 |
| Answer Relevancy | 0.687 |
| Context Precision | 0.888 |
| Context Recall | 0.695 |
| Average Latency | (check baseline.json) |

## Key Finding

There is a significant gap between the pipeline's own Judge Agent scores (typically 7-10/10
on "grounding" across the Day 19/20 test runs) and RAGAS's independently-measured
faithfulness score (0.691 average). This indicates the Judge Agent is systematically
overconfident about how well report claims are actually supported by retrieved filing
content — a real transparency gap, not just a scoring-scale mismatch, since RAGAS checks
each individual claim against the retrieved context rather than giving one holistic
impression.

Context precision (0.888) is noticeably higher than faithfulness (0.691), suggesting the
Analyst Agent's report generation step introduces claims beyond what retrieved chunks
support, independent of retrieval quality itself. This means retrieval-side fixes alone
(chunking, adaptive retry) will not fully close the gap — the Analyst prompt's grounding
instructions may also need tightening.

## Known Data Quality Notes

- Judge score for ticker **F** is a `-1` sentinel (LLM output truncated at the 4096-token
  completion limit); excluded from Judge-score averages, does not affect RAGAS numbers
  since RAGAS uses retrieved_chunks + final_report independently of Judge output.
- Ticker **BA** hit one empty-string LLM response during adaptive confidence scoring;
  handled by existing fallback (defaults to "Ambiguous"), did not affect final report
  generation.
- Several RAGAS metric evaluations failed with `LLMDidNotFinishException` (max_tokens
  reached mid-generation) or one `APITimeoutError`; these were excluded from the average
  via existing NaN-filtering rather than treated as zero, so the reported averages reflect
  only successfully-scored rows.

## What This Baseline Is For

This is the "before" reference point for later experiments:
- Day 31: Fixed vs. adaptive retrieval comparison — compare against this faithfulness/
  context_precision/context_recall baseline.
- Day 32: Fine-tuned vs. API Judge agreement — the Judge-overconfidence gap found here is
  exactly the kind of miscalibration the LoRA-distilled Judge experiment should surface
  and, ideally, correct.
