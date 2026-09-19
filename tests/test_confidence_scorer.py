import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from retrieval.confidence_scorer import score_retrieval


def test_relevant_chunks_score_correct():
    question = "What are the company's main risk factors?"
    good_chunks = [
        "Item 1A. Risk Factors: Our business faces risks related to supply chain disruptions...",
        "We are also exposed to currency fluctuation risk in our international operations..."
    ]
    with patch("retrieval.confidence_scorer.call_llm", return_value='{"label": "Correct", "reasoning": "Chunks clearly describe risk factors."}'):
        result = score_retrieval(question, good_chunks)
        assert result["label"] == "Correct"
        assert "Chunks clearly describe" in result["reasoning"]


def test_irrelevant_chunks_score_incorrect():
    question = "What are the company's main risk factors?"
    bad_chunks = [
        "Item 6. Selected Financial Data: The following table sets forth our five-year summary of operations..."
    ]
    with patch("retrieval.confidence_scorer.call_llm", return_value='{"label": "Incorrect", "reasoning": "Selected financial data contains no risk details."}'):
        result = score_retrieval(question, bad_chunks)
        assert result["label"] == "Incorrect"


def test_malformed_llm_output_defaults_to_ambiguous():
    with patch("retrieval.confidence_scorer.call_llm", return_value="I am unable to answer in JSON format."):
        result = score_retrieval("some question", ["some chunk"])
        assert result["label"] == "Ambiguous"
        assert "could not be parsed" in result["reasoning"]