"""
agents/llm_client.py

Shared LLM client for all agents in the pipeline.
Single place to configure model, API key, timeouts, and retries.
"""
import os
import httpx
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

_http_client = httpx.Client(timeout=300.0)

_llm = ChatOpenAI(
    model="openai/gpt-oss-20b",
    openai_api_key=os.getenv("NVIDIA_API_KEY"),
    openai_api_base="https://integrate.api.nvidia.com/v1",
    temperature=0.2,
    top_p=0.7,
    max_tokens=2048,
    timeout=300.0,
    max_retries=2,
)
llm = _llm  # public alias for use elsewhere

def call_llm(prompt: str) -> str:
    """Send a prompt to the configured LLM and return the response string."""
    response = _llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)
