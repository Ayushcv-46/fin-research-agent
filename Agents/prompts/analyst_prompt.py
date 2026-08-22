# agents/prompts/analyst_prompt.py

ANALYST_PROMPT_TEMPLATE = """
You are a financial research analyst. Using ONLY the information in the 
provided filing chunks and financial data below, write a structured report.

FINANCIAL DATA:
{fundamentals}

FILING CHUNKS:
{chunks}

INSTRUCTIONS:
1. Bull Case (bull_points): List 2-3 genuinely positive points (real strengths, growth 
   drivers, or competitive advantages). Each point MUST cite its source 
   in the format (Section: <section_name>).
2. Bear Case (bear_points): List 2-3 risk/negative points. Each point MUST cite its 
   source in the format (Section: <section_name>).
3. Summary (summary): Write a neutral 2-3 sentence synthesis. Do NOT recommend 
   buying or selling.
4. Citations (citations): You MUST list all distinct section names (e.g., "Item 1A.", "Item 7.", "Item 8.") cited in your bull and bear cases. This list must NOT be empty if you have cited sections in your points.
5. If you cannot support a claim using the chunks provided, do NOT 
   include it.
6. Do NOT reinterpret, soften, or reframe a risk/negative statement as a 
   positive one just to fill the Bull Case. A risk factor mentioning the 
   Company "may not" achieve something, or describing a threat, is NOT a 
   bull point — even if it mentions a related positive-sounding word.
7. If the provided chunks do not contain any genuine positive/growth 
   information, write exactly: "No significant bull case found in the 
   provided sources." as a single point in the bull case list, instead of forcing one.
"""
def build_analyst_prompt(fundamentals: dict, chunks: list) -> str:
    """
    Fills the template with real data for one manual test run.
    fundamentals: dict like {"P/E": 28.5, "Market Cap": "2.1T", ...}
    chunks: list of dicts like {"text": "...", "section": "Item 7"}
    """
    chunks_text = "\n\n".join(
        f"[Section: {c['section']}]\n{c['text']}" for c in chunks
    )
    fundamentals_text = "\n".join(f"{k}: {v}" for k, v in fundamentals.items())
    return ANALYST_PROMPT_TEMPLATE.format(
        fundamentals=fundamentals_text,
        chunks=chunks_text
    )