"""
tests/test_llm.py

Thin re-export shim so existing test scripts keep working.
The real call_llm definition lives in agents/llm_client.py.
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.llm_client import call_llm  # re-export for backwards compat

if __name__ == "__main__":
    response = call_llm("Say hello in one sentence.")
    print(response)