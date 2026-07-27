"""Environment-backed configuration for ResearchAgent."""

from __future__ import annotations

import logging
import os
from typing import Any


LOGGER = logging.getLogger(__name__)
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULTS: dict[str, Any] = {
    "model": "gpt-4o",
    "temperature": 0.7,
    "timeout": 60.0,
}


def get_config() -> dict[str, Any]:
    """Return API settings from the environment without requiring credentials at import time."""
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

    if not api_key:
        LOGGER.warning("OPENAI_API_KEY is not set; LLM requests will return an error response.")
    if "OPENAI_BASE_URL" not in os.environ:
        LOGGER.warning("OPENAI_BASE_URL is not set; using the OpenAI default endpoint.")

    return {
        "api_key": api_key,
        "base_url": base_url,
        "defaults": DEFAULTS.copy(),
    }
