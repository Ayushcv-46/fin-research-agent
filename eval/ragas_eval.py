# eval/ragas_eval.py
import math
from typing import List, Dict, Any, Optional

try:
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import faithfulness, answer_relevancy
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_huggingface import HuggingFaceEmbeddings
    from datasets import Dataset
    from ragas.dataset_schema import EvaluationResult
    RAGAS_AVAILABLE = True

    import ragas.dataset_schema as _ragas_ds

    def _safe_parse_run_traces(traces, run_id=None):
        if not traces:
            return []
        try:
            from ragas.callbacks import parse_run_traces as _orig
            return _orig(traces, run_id)
        except IndexError:
            return []

    _ragas_ds.parse_run_traces = _safe_parse_run_traces
except ImportError as _e:
    RAGAS_AVAILABLE = False
    print(f"[WARNING] RAGAS not available ({_e}).")

# Dropped context_precision and context_recall:
# - require ground truth we don't have
# - consistently timeout during experiment
# - were always null in every run
RAGAS_METRIC_NAMES = ["faithfulness", "answer_relevancy"]

_ragas_llm_wrapper = None
_ragas_emb_wrapper = None

def get_ragas_wrappers():
    global _ragas_llm_wrapper, _ragas_emb_wrapper
    if _ragas_llm_wrapper is None:
        import os
        from langchain_openai import ChatOpenAI

        ragas_llm = ChatOpenAI(
            model="openai/gpt-oss-20b",
            openai_api_key=os.getenv("NVIDIA_API_KEY"),
            openai_api_base="https://integrate.api.nvidia.com/v1",
            temperature=0.2,
            top_p=0.7,
            max_tokens=2048,
            timeout=300.0,      # increased from 120s
            max_retries=3       # increased from 2
        )
        _ragas_llm_wrapper = LangchainLLMWrapper(ragas_llm)
        _ragas_emb_wrapper = LangchainEmbeddingsWrapper(
            HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        )
    return _ragas_llm_wrapper, _ragas_emb_wrapper


def run_ragas_evaluation(pipeline_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    pipeline_results: list of dicts, one per ticker run, each with:
        - question: str
        - retrieved_chunks: list of {"text": str, "section": str, "distance": float}
        - final_report: str
    Runs faithfulness and answer_relevancy only.
    context_precision/recall dropped — require ground truth and consistently timeout.
    """
    if not RAGAS_AVAILABLE:
        return {"error": "ragas not installed"}

    rows = [
        p for p in pipeline_results
        if p.get("retrieved_chunks") and p.get("final_report")
    ]
    if not rows:
        return {"error": "no evaluable rows (missing chunks or report)"}

    dataset = Dataset.from_dict({
        "user_input": [p["question"] for p in rows],
        "response": [p["final_report"] for p in rows],
        "retrieved_contexts": [
            [c["text"] for c in p["retrieved_chunks"]] for p in rows
        ],
        "reference": [p["final_report"] for p in rows],  # proxy reference
    })

    try:
        judge, embeddings = get_ragas_wrappers()

        # Set reproducibility=1 at object level before passing to evaluate
        # Forces single LLM call per metric instead of 3
        faithfulness.reproducibility = 1
        answer_relevancy.reproducibility = 1

        metrics = [faithfulness, answer_relevancy]

        print(f"[RAGAS] evaluating {len(rows)} rows x 2 metrics...")
        result = ragas_evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=judge,
            embeddings=embeddings,
            raise_exceptions=False,
        )
        if not isinstance(result, EvaluationResult):
            raise RuntimeError("ragas.evaluate() returned an Executor instead of EvaluationResult")

        scores: Dict[str, Any] = {}
        for name in RAGAS_METRIC_NAMES:
            vals = []
            for row in result.scores:
                v = row.get(name)
                if v is None:
                    continue
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    continue
                if math.isnan(fv):
                    continue
                vals.append(fv)
            scores[name] = round(sum(vals) / len(vals), 3) if vals else None

        print(f"[RAGAS] scores: {scores}")
        return scores

    except Exception as e:
        import traceback
        print("[RAGAS][ERROR]")
        traceback.print_exc()
        return {"error": str(e)}