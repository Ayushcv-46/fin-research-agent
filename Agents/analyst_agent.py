from pydantic import BaseModel, Field
from agents.prompts.analyst_prompt import build_analyst_prompt
from agents.data_agent import GraphState  # shared state schema
from agents.llm_client import llm


class ReportDraft(BaseModel):
    bull_points: list[str] = Field(description="Up to 3 bullish points genuinely supported by the source chunks, each citing (Section: <section_name>). Return an empty list if no bull case is supported by the chunks.")
    bear_points: list[str] = Field(description="Up to 3 bearish points genuinely supported by the source chunks, each citing (Section: <section_name>). Return an empty list if no bear case is supported by the chunks.")
    summary: str = Field(description="Neutral synthesis, no buy/sell recommendation")
    citations: list[str] = Field(description="List of distinct section names cited in the bull and bear points, e.g., ['Item 1A.', 'Item 7.', 'Item 8.']")


def analyst_agent_node(state: GraphState) -> dict:
    chunks = state["retrieved_chunks"]
    fundamentals = state.get("fundamentals", {})

    if not chunks:
        draft = ReportDraft(
            bull_points=[],
            bear_points=[],
            summary="Insufficient filing data retrieved to generate analysis.",
            citations=[]
        )
        return {"report_draft": draft.model_dump()}

    prompt = build_analyst_prompt(fundamentals, chunks)
    llm_with_schema = llm.with_structured_output(ReportDraft)

    try:
        report_draft = llm_with_schema.invoke(prompt)
        if isinstance(report_draft, ReportDraft):
            report_dict = report_draft.model_dump()
        elif isinstance(report_draft, dict):
            report_dict = report_draft
        else:
            raise ValueError(f"Unexpected response type: {type(report_draft)}")
    except Exception as e:
        report_dict = ReportDraft(
            bull_points=[], bear_points=[],
            summary=f"Analyst generation failed: {str(e)}",
            citations=[]
        ).model_dump()

    return {"report_draft": report_dict}