import os
from dotenv import load_dotenv

# Load real environment variables from .env first if present
load_dotenv()

# Set fallback dummy values so unit tests without .env or real keys never crash on import
os.environ.setdefault("GEMINI_API_KEY", "dummy-test-key-for-unit-tests")
os.environ.setdefault("GEMINI_MODEL", "gemini-3.5-flash-lite")
