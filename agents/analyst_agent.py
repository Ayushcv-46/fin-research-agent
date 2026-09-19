from pydantic import BaseModel, Field
import json
import re
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
    
    json_instructions = """
Please output ONLY a valid JSON object matching the following structure exactly. Do not wrap it in markdown block quotes or add any extra text before or after:
{
  "bull_points": ["string", "string", ...],
  "bear_points": ["string", "string", ...],
  "summary": "string",
  "citations": ["string", "string", ...]
}
"""
    prompt += json_instructions

    try:
        response = llm.invoke(prompt)
        text_response = response.content if hasattr(response, 'content') else str(response)
        
        # Clean markdown wraps if the LLM ignores instructions
        match = re.search(r"\{.*\}", text_response, re.DOTALL)
        if match:
            text_response = match.group(0)
            
        parsed_dict = json.loads(text_response)
        
        # Validate through Pydantic to ensure all fields are present
        report_dict = ReportDraft(**parsed_dict).model_dump()
    except Exception as e:
        report_dict = ReportDraft(
            bull_points=[], bear_points=[],
            summary=f"Analyst generation failed: {str(e)}",
            citations=[]
        ).model_dump()

    return {"report_draft": report_dict}