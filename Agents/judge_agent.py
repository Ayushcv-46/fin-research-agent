from pydantic import BaseModel
from agents.llm_client import llm
from agents.prompts.judge_prompt import build_judge_prompt


class JudgeScore(BaseModel):
    grounding: int
    completeness: int
    clarity: int
    overall: int
    flagged_issues: list[str]


FALLBACK_JUDGE_SCORE = {
    "grounding": -1,
    "completeness": -1,
    "clarity": -1,
    "overall": -1,
    "flagged_issues": ["Judge evaluation failed — LLM call error, this score is not real"],
}


def judge_agent_node(state: dict) -> dict:
    report_draft = state.get("report_draft", {})
    retrieved_chunks = state.get("retrieved_chunks", [])

    prompt = build_judge_prompt(report_draft, retrieved_chunks)
    structured_llm = llm.with_structured_output(JudgeScore)

    try:
        result = structured_llm.invoke(prompt)
        return {"judge_score": result.model_dump()}
    except Exception as e:
        print(f"[judge_agent_node] LLM call failed: {e}")
        return {"judge_score": FALLBACK_JUDGE_SCORE}