# Adaptive Retrieval Design

## 1. Relevance Scoring
- Lightweight LLM call scores retrieved chunks as Correct / Ambiguous / Incorrect (CRAG-style)
- Output: structured JSON { label, reasoning }
- Implemented Day 11 in retrieval/confidence_scorer.py

## 2. Retry & Reformulation Logic
- If label != Correct: call reformulate_query(question, label, reasoning, chunks_so_far)
- Reformulated query re-queries ChromaDB
- Ambiguous results kept as fallback candidates (not discarded); Incorrect results discarded

## 3. Max Retry Limit
- Max 3 attempts total
- Stop early if Correct is reached
- If no Correct after 3 attempts: fall back to best-scoring Ambiguous attempt (best-of-N)
- Never returns empty chunks to Analyst Agent

## 4. State Changes
- GraphState extended with: retrieval_confidence (str), retrieval_reasoning (str)
- Passed downstream to Analyst, Judge, and UI transparency panel

## 5. Conditional Edge Sketch
retriever_node -> confidence_check -> 
    if Correct: proceed to analyst_node
    if Incorrect/Ambiguous and retries < 3: retry_retrieval (loop back with reformulated query)
    if retries == 3: proceed to analyst_node with best-of-N chunks