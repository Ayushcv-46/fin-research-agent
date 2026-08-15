import os
import sys
import json
import re

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.test_llm import call_llm


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

    # Clean up markdown formatting if present
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    result = None
    try:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            result = json.loads(match.group(0))
        else:
            # If LLM omitted the closing brace
            candidate = cleaned if cleaned.startswith("{") else "{" + cleaned.split("{", 1)[-1]
            if not candidate.endswith("}"):
                candidate = candidate + "}"
            result = json.loads(candidate)

        if not isinstance(result, dict) or "label" not in result or result["label"] not in ("Correct", "Ambiguous", "Incorrect"):
            raise ValueError("Missing or invalid label field")

    except Exception:
        print(f"[confidence_scorer] Failed to parse LLM output: {raw_response!r}")
        # Secondary fallback: regex search for label
        label_match = re.search(r'"label"\s*:\s*"(Correct|Ambiguous|Incorrect)"', raw_response, re.IGNORECASE)
        if label_match:
            label = label_match.group(1).capitalize()
            reasoning_match = re.search(r'"reasoning"\s*:\s*"(.*?)"', raw_response, re.DOTALL)
            reasoning = reasoning_match.group(1) if reasoning_match else "Extracted via fallback."
            result = {"label": label, "reasoning": reasoning}
        else:
            result = {
                "label": "Ambiguous",
                "reasoning": "Failed to parse scorer output; defaulting to Ambiguous."
            }


    return result