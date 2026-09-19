"""
agents/llm_client.py

Shared Google Gemini LLM client for all agents in the pipeline.
Configures model, API key, timeouts, and built-in retries.
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Please define GEMINI_API_KEY in your .env file."
    )

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

_llm = ChatOpenAI(
    model=GEMINI_MODEL,
    openai_api_key=GEMINI_API_KEY,
    openai_api_base="https://generativelanguage.googleapis.com/v1beta/openai/",
    temperature=0.2,
    top_p=0.7,
    max_tokens=2048,
    timeout=120.0,
    max_retries=3,
)

llm = _llm  # public alias for use across agents


def call_llm(prompt: str) -> str:
    """Send a prompt to the configured LLM and return the response string."""
    response = _llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)
