"""
games/env_validator.py
──────────────────────
Validates the GEMINI_API_KEY from the environment by making a lightweight
API call.  Designed to be run in a background thread.
"""

import os


def validate_env() -> tuple[bool, str | None, str]:
    """
    Return (valid, key, message).

    - valid  : True if the key exists and passes a live API ping.
    - key    : the raw key string on success, None on failure.
    - message: human-readable result to display in the UI.
    """
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return False, None, "GEMINI_API_KEY not found in .env"

    try:
        from google import genai  # type: ignore
        client = genai.Client(api_key=key)
        _ = client.models.list()   # lightweight ping
        return True, key, "API key validated ✓"
    except Exception as exc:
        short = str(exc)[:60]
        return False, None, f"Key invalid: {short}"