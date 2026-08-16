import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from retrieval.confidence_scorer import score_retrieval



def test_relevant_chunks_score_correct():
    question = "What are the company's main risk factors?"
    good_chunks = [
        "Item 1A. Risk Factors: Our business faces risks related to supply chain disruptions...",
        "We are also exposed to currency fluctuation risk in our international operations..."
    ]
    result = score_retrieval(question, good_chunks)
    assert result["label"] in ("Correct", "Ambiguous")
    print("PASS: relevant chunks ->", result["label"], "-", result["reasoning"])


def test_irrelevant_chunks_score_incorrect():
    question = "What are the company's main risk factors?"
    bad_chunks = [
        "Item 6. Selected Financial Data: The following table sets forth our five-year summary of operations..."
    ]
    result = score_retrieval(question, bad_chunks)
    assert result["label"] in ("Incorrect", "Ambiguous")
    print("PASS: irrelevant chunks ->", result["label"], "-", result["reasoning"])


def test_malformed_llm_output_defaults_to_ambiguous(monkeypatch):
    """Simulates the LLM returning garbage — scorer should not crash."""
    import retrieval.confidence_scorer as cs
    monkeypatch.setattr(cs, "call_llm", lambda prompt: "I'm not sure, sorry!")
    result = cs.score_retrieval("some question", ["some chunk"])
    assert result["label"] == "Ambiguous"
    print("PASS: malformed output handled ->", result["label"])


if __name__ == "__main__":
    test_relevant_chunks_score_correct()
    test_irrelevant_chunks_score_incorrect()
    print("Run test_malformed_llm_output_defaults_to_ambiguous via pytest (needs monkeypatch).")