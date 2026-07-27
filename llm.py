"""Small async wrapper for OpenAI-compatible chat-completions APIs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import httpx  # type: ignore[reportMissingImports]


LOGGER = logging.getLogger(__name__)
DEFAULT_BASE_URL = "https://api.openai.com/v1"


@dataclass(slots=True)
class FunctionCall:
    """The function requested by an OpenAI tool call."""

    name: str
    arguments: str


@dataclass(slots=True)
class ToolCall:
    """A normalized tool call returned by a chat-completions provider."""

    id: str
    function: FunctionCall
    type: str = "function"


@dataclass(slots=True)
class ChatResponse:
    """Normalized chat result that callers can use independently of provider details."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    error: str | None = None


class LLMClient:
    """Call an OpenAI-compatible ``/chat/completions`` endpoint through httpx."""

    def __init__(
        self,
        api_key: str | None,
        base_url: str | None = None,
        model: str = "gpt-4o",
    ) -> None:
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.model = model

    @property
    def endpoint(self) -> str:
        """Return a chat-completions URL for the configured base URL."""
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> ChatResponse:
        """Send messages and return content plus normalized function tool calls.

        API, transport, and malformed-response failures are represented on the
        returned response's ``error`` attribute so agent loops can decide how
        to recover without an unhandled request exception.
        """
        if not self.api_key:
            return ChatResponse(error="OPENAI_API_KEY is not configured.")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "temperature": temperature,
        }
        if tools is not None:
            payload["tools"] = list(tools)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = _error_detail(exc.response)
            message = f"LLM API returned HTTP {exc.response.status_code}: {detail}"
            LOGGER.warning(message)
            return ChatResponse(error=message)
        except httpx.RequestError as exc:
            message = f"LLM API request failed: {exc}"
            LOGGER.warning(message)
            return ChatResponse(error=message)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            message = f"LLM API returned an invalid JSON response: {exc}"
            LOGGER.warning(message)
            return ChatResponse(error=message)

        return _parse_response(data)


def _parse_response(data: Any) -> ChatResponse:
    """Convert a provider response document into the public response shape."""
    if not isinstance(data, dict):
        return ChatResponse(error="LLM API response must be a JSON object.")

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ChatResponse(error="LLM API response did not include any choices.")

    choice = choices[0]
    if not isinstance(choice, dict) or not isinstance(choice.get("message"), dict):
        return ChatResponse(error="LLM API response did not include a valid message.")

    message = choice["message"]
    return ChatResponse(
        content=_content_to_text(message.get("content")),
        tool_calls=_parse_tool_calls(message),
    )


def _parse_tool_calls(message: Mapping[str, Any]) -> list[ToolCall]:
    """Normalize modern ``tool_calls`` and legacy ``function_call`` payloads."""
    raw_calls = message.get("tool_calls", [])
    if not isinstance(raw_calls, list):
        raw_calls = []

    legacy_call = message.get("function_call")
    if isinstance(legacy_call, dict):
        raw_calls.append({"id": "legacy_function_call", "function": legacy_call})

    tool_calls: list[ToolCall] = []
    for index, raw_call in enumerate(raw_calls):
        if not isinstance(raw_call, dict) or not isinstance(raw_call.get("function"), dict):
            continue

        function = raw_call["function"]
        name = function.get("name")
        if not isinstance(name, str) or not name:
            continue

        arguments = function.get("arguments", "{}")
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments, ensure_ascii=False)

        tool_calls.append(
            ToolCall(
                id=str(raw_call.get("id") or f"tool_call_{index}"),
                type=str(raw_call.get("type") or "function"),
                function=FunctionCall(name=name, arguments=arguments),
            )
        )
    return tool_calls


def _content_to_text(content: Any) -> str:
    """Handle the string and multipart content shapes used by compatible APIs."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    return ""


def _error_detail(response: httpx.Response) -> str:
    """Extract a concise provider error message without raising another exception."""
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        return response.text[:500] or "no error detail"

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(error, str):
            return error
    return "no error detail"
