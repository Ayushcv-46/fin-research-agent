"""Optional exploratory RAGAS evaluation using the configured Gemini client.

Scores are approximate LLM-as-judge signals. No generated answer is used as its
own reference; RAGAS faithfulness and answer relevancy do not need one here.
"""
import math
from typing import Any, Optional

try:
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import faithfulness, answer_relevancy
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_huggingface import HuggingFaceEmbeddings
    from datasets import Dataset
    from ragas.dataset_schema import EvaluationResult
    RAGAS_AVAILABLE = True
except ImportError as exc:
    RAGAS_AVAILABLE = False
    print(f"[WARNING] RAGAS not available ({exc}).")

_wrappers = None


def get_ragas_wrappers():
    global _wrappers
    if _wrappers is None:
        from agents.llm_client import llm
        _wrappers = (
            LangchainLLMWrapper(llm),
            LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")),
        )
    return _wrappers


def run_ragas_evaluation(pipeline_results: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not RAGAS_AVAILABLE:
        return {"error": "ragas not installed"}
    rows = [p for p in pipeline_results if p.get("retrieved_chunks") and p.get("final_report")]
    if not rows:
        return {"error": "no evaluable rows (missing chunks or report)"}
    dataset = Dataset.from_dict({
        "user_input": [p["question"] for p in rows],
        "response": [p["final_report"] for p in rows],
        "retrieved_contexts": [[c["text"] for c in p["retrieved_chunks"]] for p in rows],
    })
    try:
        judge, embeddings = get_ragas_wrappers()
        faithfulness.reproducibility = 1
        answer_relevancy.reproducibility = 1
        result = ragas_evaluate(dataset=dataset, metrics=[faithfulness, answer_relevancy],
                                llm=judge, embeddings=embeddings, raise_exceptions=False)
        if not isinstance(result, EvaluationResult):
            raise RuntimeError("ragas.evaluate() returned an Executor instead of EvaluationResult")
        scores = {}
        for name in ("faithfulness", "answer_relevancy"):
            vals = []
            for row in result.scores:
                try:
                    value = float(row[name])
                    if not math.isnan(value):
                        vals.append(value)
                except (KeyError, TypeError, ValueError):
                    continue
            scores[name] = round(sum(vals) / len(vals), 3) if vals else None
        return scores
    except Exception as exc:
        return {"error": str(exc)}
