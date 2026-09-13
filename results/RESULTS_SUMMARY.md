# Research Results Summary

## Finding 1: Adaptive Retrieval
No meaningful improvement over fixed top-k retrieval (answer relevancy: 0.743 fixed vs 0.728 adaptive across 12 tickers). Retry rate of 50% suggests the confidence threshold may be too aggressive. Faithfulness was unmeasurable due to evaluation-LLM token limits.

## Finding 2: Judge Distillation Agreement
The LoRA-finetuned judge shows weak-to-moderate correlation with the API judge (overall: r=0.398, p=0.201, not statistically significant at n=12), but reasonable practical agreement — 83.3% of scores fall within ±2 points. Both judges flag issues on 100% of reports.

## Finding 3: Cost/Latency
Fine-tuned judge inference eliminated per-call API cost ($0.000112/report for API vs $0.0 for fine-tuned) but was slower on average (11.81s vs 7.82s per report on a Colab T4). This is likely because the fine-tuned path runs raw, unbatched HF-style generation on 4-bit quantized weights, without the continuous-batching/paged-attention optimizations a production serving stack like NVIDIA NIM provides. Distillation removed cost at the expense of latency — closing that gap would require serving infrastructure investment beyond the fine-tuning itself, not further model changes.