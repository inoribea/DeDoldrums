"""Environment configuration for role-specific LLM routing."""

from __future__ import annotations

import os
from typing import Any, Mapping

try:
    from .llm import PROVIDER_REGISTRY
except ImportError:  # Supports direct execution from the package directory.
    from llm import PROVIDER_REGISTRY


ROLES = ("tool_calling", "creative", "conversational", "content_review")


def _provider_env_name(provider: str) -> str:
    return provider.upper().replace("-", "_")


def get_router_config() -> dict[str, Mapping[str, Any]]:
    """Parse ``LLM_{ROLE}=provider/model`` variables into router configuration.

    Every role inherits the tool-calling configuration unless explicitly configured.
    """
    configured: dict[str, dict[str, Any]] = {}
    for role in ROLES:
        value = os.getenv(f"LLM_{role.upper()}")
        if not value:
            continue
        provider, separator, model = value.partition("/")
        if not separator or not provider or not model:
            raise ValueError(
                f"LLM_{role.upper()} must use the format provider/model"
            )
        registry = PROVIDER_REGISTRY.get(provider)
        if registry is None:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        env_provider = _provider_env_name(provider)
        configured[role] = {
            "backend": registry["backend"],
            "provider": provider,
            "model": model,
            "api_key": os.getenv(f"{env_provider}_API_KEY"),
            "base_url": os.getenv(
                f"{env_provider}_BASE_URL", str(registry["default_base"])
            ).rstrip("/"),
        }

    if "tool_calling" not in configured:
        raise ValueError("LLM_TOOL_CALLING must be configured")

    tool_calling = configured["tool_calling"]
    return {role: configured.get(role, tool_calling.copy()) for role in ROLES}


def get_config() -> dict[str, Any]:
    """Return legacy single-client settings derived from the tool-calling role."""
    config = get_router_config()["tool_calling"]
    return {
        "api_key": config["api_key"],
        "base_url": config["base_url"],
        "model": config["model"],
        "defaults": {"temperature": 0.7, "timeout": 60.0},
    }
