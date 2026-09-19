import os

# Set dummy API key for testing before any project modules or agents are imported
os.environ.setdefault("GEMINI_API_KEY", "dummy-test-key-for-unit-tests")
os.environ.setdefault("GEMINI_MODEL", "gemini-3.5-flash-lite")
