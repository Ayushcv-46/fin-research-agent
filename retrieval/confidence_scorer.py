import os
import sys
import logging
from typing import Literal
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.llm_client import call_llm
from agents.json_utils import parse_and_validate_json

logger = logging.getLogger(__name__)


class ConfidenceResult(BaseModel):
    label: Literal["Correct", "Ambiguous", "Incorrect"]
    reasoning: str = Field(description="One sentence justification of the score")


SCORING_PROMPT = """You are grading whether retrieved text is sufficient to answer a financial research question.

Question: {question}

Retrieved chunks:
{chunks_text}

Grade the retrieval as one of: "Correct", "Ambiguous", "Incorrect".
- Correct: the chunks contain enough information to fully answer the question.
- Ambiguous: the chunks are somewhat relevant but incomplete or unclear.
- Incorrect: the chunks do not help answer the question at all.

Respond ONLY in this JSON format:
{{"label": "<Correct|Ambiguous|Incorrect>", "reasoning": "<one sentence>"}}
"""


def score_retrieval(question: str, chunks: list[str]) -> dict:
    """
    Grades whether retrieved chunks are sufficient to answer `question`.

    Inputs:
        question: the user's research question (str)
        chunks: list of retrieved chunk texts (list[str])

    Output:
        dict with keys "label" (Correct/Ambiguous/Incorrect) and "reasoning" (str)
    """
    chunks_text = "\n\n".join(f"- {c}" for c in chunks)
    prompt = SCORING_PROMPT.format(question=question, chunks_text=chunks_text)
    raw_response = call_llm(prompt)

    try:
        validated = parse_and_validate_json(raw_response, ConfidenceResult)
        return validated.model_dump()
    except ValueError as err:
        logger.warning(
            "Failed to parse confidence scorer LLM output: %s. Raw output: %r. Defaulting to 'Ambiguous'.",
            err,
            raw_response,
        )
        return {
            "label": "Ambiguous",
            "reasoning": "Confidence evaluation output could not be parsed; defaulting to Ambiguous.",
        }



def confidence_scorer_node(state: dict) -> dict:
    """
    Evaluates the retrieved chunks against the original question.
    Returns confidence_label (Correct/Ambiguous/Incorrect) and confidence_reasoning.
    """
    result = score_retrieval(state["question"], state["retrieved_chunks"])
    return {
        "confidence_label": result["label"],
        "confidence_reasoning": result["reasoning"],
    }