# Financial Research Analyst

A 5-agent LangGraph pipeline (Data, Retriever, Analyst, Judge, Report) that answers questions about a company SEC 10-K filing, with adaptive retrieval, an LLM judge, a FastAPI backend with SSE streaming, and an HTML/Tailwind frontend.

## Run locally

1. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` (and `GEMINI_MODEL` if you want a different model).
2. Start the backend from the project root:
```bash
   source venv/bin/activate
   export PYTHONPATH=.
   RETRIEVAL_MODE=fixed uvicorn app.main:app --host 0.0.0.0 --port 8000
```
   `RETRIEVAL_MODE=adaptive` enables the retrieval retry loop. Once the embedding model is cached, add `HF_HUB_OFFLINE=1` to skip network checks at startup.
3. Serve the frontend in a second terminal and open http://localhost:3000:
```bash
   python3 -m http.server 3000 -d frontend
```
4. Run the tests with `pytest -q` (live tests are skipped by default).

## Performance notes

- The streaming endpoint used to run the pipeline twice (`GRAPH.stream()` then `GRAPH.invoke()`); it now runs once.
- The retriever no longer embeds chunks twice (`chunk_filing` already embeds).
- Warm ticker (filing already ingested), fixed mode, gemini-3.5-flash-lite, WSL on a laptop: 7.6 to 12.3 s over 6 runs.
- Adaptive mode retries retrieval up to 2 times when the confidence scorer returns Incorrect or Ambiguous. Verified with an off-topic question: 2 retries, then the pipeline proceeds to the analyst.
- `scripts/benchmark_timing.py` measures per-node timing. It deletes the AAPL collection for its cold run.

## Known issues

- Cold-ticker ingestion is slow and under investigation (AAPL took roughly 270 to 300 s in the benchmark script).
- The judge only sees retrieved filing chunks, so market data in the summary (P/E, market cap) can be flagged as ungrounded.
- The `judge_mode` request parameter is validated but not yet used: the judge backend is chosen by the `JUDGE_MODE` environment variable at startup.

## Limitations

- The API judge and the analyst use the same model family, and scores vary between runs (6 to 10 out of 10 for the same question and filing).
- Report quality depends on retrieval: for a "growth drivers" question the bull case was descriptive.
- After 2 failed retrievals the pipeline still writes a report.
- Judge-overconfidence and fine-tuned-judge results were measured with the previous LLM provider.
- The fine-tuned judge (`JUDGE_MODE=finetuned`) needs a GPU and was not exercised in this demo path.
- Tickers are letters-only (no BRK.B).
