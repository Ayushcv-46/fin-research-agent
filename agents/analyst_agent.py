from pydantic import BaseModel, Field
from agents.prompts.analyst_prompt import build_analyst_prompt
from agents.data_agent import GraphState  # shared state schema
from agents.llm_client import llm
from agents.json_utils import invoke_json



class ReportDraft(BaseModel):
    overview: str = Field(default="", description="Plain-language answer to the user's question, with key context and relevant facts.")
    bull_points: list[str] = Field(
        default_factory=list,
        description="Up to 3 bullish points genuinely supported by the source chunks, each citing (Section: <section_name>).",
    )
    bear_points: list[str] = Field(
        default_factory=list,
        description="Up to 3 bearish points genuinely supported by the source chunks, each citing (Section: <section_name>).",
    )
    summary: str = Field(default="", description="Short neutral takeaway that answers the question, with no buy/sell recommendation")
    citations: list[str] = Field(
        default_factory=list,
        description="List of distinct section names cited in the bull and bear points, e.g., ['Item 1A.', 'Item 7.', 'Item 8.']",
    )


def analyst_agent_node(state: GraphState) -> dict:
    chunks = state.get("retrieved_chunks") or []
    fundamentals = state.get("fundamentals") or {}

    if not chunks:
        draft = ReportDraft(
            overview="The latest filing did not provide enough relevant information to answer this question.",
            bull_points=[],
            bear_points=[],
            summary="Insufficient filing data retrieved to generate analysis.",
            citations=[],
        )
        return {"report_draft": draft.model_dump()}

    prompt = build_analyst_prompt(fundamentals, chunks, state.get("question", ""))
    json_instructions = """
Please output ONLY a valid JSON object matching the following structure exactly. Do not wrap it in markdown block quotes or add any extra text before or after:
{
  "overview": "plain-language answer focused on the research question",
  "bull_points": ["string", "string", ...],
  "bear_points": ["string", "string", ...],
  "summary": "string",
  "citations": ["string", "string", ...]
}
"""
    full_prompt = prompt + json_instructions

    draft = invoke_json(llm, full_prompt, ReportDraft)
    return {"report_draft": draft.model_dump()}
