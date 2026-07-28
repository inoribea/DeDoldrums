"""Raw HTTP LLM backends and a role-aware router."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import httpx  # pyright: ignore[reportMissingImports]
import logging


LOGGER = logging.getLogger(__name__)


PROVIDER_REGISTRY = {
    "openai": {"backend": "response", "default_base": "https://api.openai.com/v1"},
    "anthropic": {"backend": "messages", "default_base": "https://api.anthropic.com/v1"},
    "deepseek": {"backend": "chat", "default_base": "https://api.deepseek.com"},
    "zhipu": {"backend": "chat", "default_base": "https://open.bigmodel.cn/api/paas/v4"},
    "kimi": {"backend": "chat", "default_base": "https://api.moonshot.cn/v1"},
    "openai-completion": {
        "backend": "completions",
        "default_base": "https://api.openai.com/v1",
    },
    "google": {
        "backend": "v1beta",
        "default_base": "https://generativelanguage.googleapis.com/v1beta",
    },
}


@dataclass(slots=True)
class FunctionCall:
    name: str
    arguments: str


@dataclass(slots=True)
class ToolCall:
    id: str
    function: FunctionCall
    type: str = "function"


@dataclass(slots=True)
class ChatResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    error: str | None = None


def _content_to_text(content: Any) -> str:
    """Convert plain or multipart message content to text."""
    if isinstance(content, str):
        return content
    if not isinstance(content, Sequence) or isinstance(content, (bytes, bytearray)):
        return "" if content is None else str(content)

    parts: list[str] = []
    for part in content:
        if isinstance(part, Mapping):
            text = part.get("text")
            if isinstance(text, str):
                parts.append(text)
        elif isinstance(part, str):
            parts.append(part)
    return "".join(parts)


def _error_detail(response: httpx.Response) -> str:
    """Return an API error message without assuming a response schema."""
    try:
        payload = response.json()
    except (json.JSONDecodeError, ValueError):
        return response.text or f"HTTP {response.status_code}"

    if isinstance(payload, Mapping):
        error = payload.get("error", payload)
        if isinstance(error, Mapping):
            message = error.get("message")
            if message:
                return str(message)
        if isinstance(error, str):
            return error
    return response.text or f"HTTP {response.status_code}"


def _tool_definition(tool: Mapping[str, Any]) -> Mapping[str, Any]:
    function = tool.get("function")
    return function if isinstance(function, Mapping) else tool


def _tool_arguments(arguments: Any) -> str:
    return arguments if isinstance(arguments, str) else json.dumps(arguments or {})


def _normalize_messages(messages: Sequence[Mapping[str, Any]] | str) -> list[dict[str, Any]]:
    """Convert a plain string or sequence of mappings into a message list."""
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    return [dict(m) if isinstance(m, Mapping) else {"role": "user", "content": str(m)} for m in messages]


def _parse_tool_calls(message: Mapping[str, Any]) -> list[ToolCall]:
    """Extract normalized ToolCall objects from a chat-completions message."""
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
        tool_calls.append(ToolCall(
            id=str(raw_call.get("id") or f"tool_call_{index}"),
            function=FunctionCall(name=name, arguments=arguments),
        ))
    return tool_calls


def _parse_chat_response(data: Mapping[str, Any] | None) -> ChatResponse:
    """Parse a standard ``/chat/completions`` response."""
    if data is None:
        return ChatResponse(error="Empty API response")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ChatResponse(error="No choices in response")
    choice = choices[0]
    if not isinstance(choice, Mapping):
        return ChatResponse(error="Invalid choice format")
    message = choice.get("message")
    if not isinstance(message, Mapping):
        return ChatResponse(error="No message in choice")
    return ChatResponse(
        content=_content_to_text(message.get("content")),
        tool_calls=_parse_tool_calls(message),
    )


class BaseBackend:
    """Shared raw-http backend plumbing."""

    def __init__(self, api_key: str | None, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.strip().rstrip("/")
        self.model = model

    async def _post(
        self,
        path: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
    ) -> tuple[Mapping[str, Any] | None, str | None]:
        try:
            # Estimate token count for diagnostic logging.
            payload_str = json.dumps(payload, ensure_ascii=False)
            est_tokens = len(payload_str) // 4
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}{path}", json=payload, headers=headers
                )
            if response.is_error:
                detail = _error_detail(response)
                LOGGER.warning("LLM %s error (~%d est tokens): %s", path, est_tokens, detail[:200])
                return None, detail
            data = response.json()
            if not isinstance(data, Mapping):
                LOGGER.warning(
                    "LLM %s returned non-object (~%d est tokens): %s",
                    path, est_tokens, type(data).__name__,
                )
                return None, "Invalid API response: expected a JSON object"
            # Log suspiciously small responses for context-overflow diagnosis.
            if not data:
                LOGGER.warning(
                    "LLM %s returned empty object (~%d est tokens) — possible context overflow",
                    path, est_tokens,
                )
            return data, None
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
            LOGGER.warning("LLM %s request failed: %s", path, str(exc)[:200])
            return None, str(exc)

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]] | str,
        tools: Sequence[Mapping[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> ChatResponse:
        raise NotImplementedError


class ChatBackend(BaseBackend):
    """Standard OpenAI-compatible ``/chat/completions`` backend.

    Used by DeepSeek, Kimi, Zhipu, and most third-party providers.
    """

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]] | str,
        tools: Sequence[Mapping[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": _normalize_messages(messages),
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = list(tools)

        data, error = await self._post(
            "/chat/completions",
            payload,
            {"Authorization": f"Bearer {self.api_key or ''}"},
        )
        if error:
            return ChatResponse(error=error)
        return _parse_chat_response(data)


class ResponseBackend(BaseBackend):
    """OpenAI Responses-compatible ``/responses`` backend."""

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]] | str,
        tools: Sequence[Mapping[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": messages if isinstance(messages, str) else list(messages),
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = list(tools)

        data, error = await self._post(
            "/responses", payload, {"Authorization": f"Bearer {self.api_key or ''}"}
        )
        if error:
            return ChatResponse(error=error)

        text: list[str] = []
        calls: list[ToolCall] = []
        for item in data.get("output", []) if data else []:
            if not isinstance(item, Mapping):
                continue
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if isinstance(content, Mapping) and content.get("type") == "output_text":
                        text.append(_content_to_text(content.get("text")))
            elif item.get("type") == "function_call":
                calls.append(
                    ToolCall(
                        id=str(item.get("call_id", "")),
                        function=FunctionCall(
                            name=str(item.get("name", "")),
                            arguments=_tool_arguments(item.get("arguments")),
                        ),
                    )
                )
        return ChatResponse(content="".join(text), tool_calls=calls)


class MessagesBackend(BaseBackend):
    """Anthropic Messages-compatible ``/messages`` backend."""

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]] | str,
        tools: Sequence[Mapping[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> ChatResponse:
        source = [{"role": "user", "content": messages}] if isinstance(messages, str) else messages
        system: list[str] = []
        remaining: list[Mapping[str, Any]] = []
        for message in source:
            if message.get("role") == "system":
                system.append(_content_to_text(message.get("content")))
            else:
                remaining.append(message)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": remaining,
            "temperature": temperature,
            "max_tokens": 4096,
        }
        if system:
            payload["system"] = "\n".join(system)
        if tools:
            payload["tools"] = [
                {
                    "name": str(definition.get("name", "")),
                    "description": str(definition.get("description", "")),
                    "input_schema": definition.get("parameters", definition.get("input_schema", {})),
                }
                for tool in tools
                for definition in [_tool_definition(tool)]
            ]

        data, error = await self._post(
            "/messages",
            payload,
            {"x-api-key": self.api_key or "", "anthropic-version": "2023-06-01"},
        )
        if error:
            return ChatResponse(error=error)

        text: list[str] = []
        calls: list[ToolCall] = []
        for block in data.get("content", []) if data else []:
            if not isinstance(block, Mapping):
                continue
            if block.get("type") == "text":
                text.append(_content_to_text(block.get("text")))
            elif block.get("type") == "tool_use":
                calls.append(
                    ToolCall(
                        id=str(block.get("id", "")),
                        function=FunctionCall(
                            name=str(block.get("name", "")),
                            arguments=_tool_arguments(block.get("input")),
                        ),
                    )
                )
        return ChatResponse(content="".join(text), tool_calls=calls)


class CompletionsBackend(BaseBackend):
    """Legacy OpenAI-compatible ``/completions`` backend."""

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]] | str,
        tools: Sequence[Mapping[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> ChatResponse:
        del tools
        if isinstance(messages, str):
            prompt = messages
        else:
            prompt = "\n".join(
                f"{message.get('role', 'user')}: {_content_to_text(message.get('content'))}"
                for message in messages
            )
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": 4096,
        }
        data, error = await self._post(
            "/completions", payload, {"Authorization": f"Bearer {self.api_key or ''}"}
        )
        if error:
            return ChatResponse(error=error)

        choices = data.get("choices", []) if data else []
        first = choices[0] if choices else {}
        return ChatResponse(content=_content_to_text(first.get("text")) if isinstance(first, Mapping) else "")


class V1BetaBackend(BaseBackend):
    """Google Generative Language ``/v1beta`` backend."""

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]] | str,
        tools: Sequence[Mapping[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> ChatResponse:
        source = [{"role": "user", "content": messages}] if isinstance(messages, str) else messages
        system: list[str] = []
        contents: list[dict[str, Any]] = []
        for message in source:
            content = _content_to_text(message.get("content"))
            if message.get("role") == "system":
                system.append(content)
            else:
                role = "model" if message.get("role") == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": content}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(system)}]}
        if tools:
            payload["tools"] = [{"functionDeclarations": [
                {
                    "name": str(definition.get("name", "")),
                    "description": str(definition.get("description", "")),
                    "parameters": definition.get("parameters", definition.get("input_schema", {})),
                }
                for tool in tools
                for definition in [_tool_definition(tool)]
            ]}]

        data, error = await self._post(
            f"/models/{self.model}:generateContent",
            payload,
            {"x-goog-api-key": self.api_key or ""},
        )
        if error:
            return ChatResponse(error=error)

        candidates = data.get("candidates", []) if data else []
        candidate = candidates[0] if candidates else {}
        content = candidate.get("content", {}) if isinstance(candidate, Mapping) else {}
        parts = content.get("parts", []) if isinstance(content, Mapping) else []
        text: list[str] = []
        calls: list[ToolCall] = []
        for index, part in enumerate(parts):
            if not isinstance(part, Mapping):
                continue
            if "text" in part:
                text.append(_content_to_text(part.get("text")))
            function_call = part.get("functionCall")
            if isinstance(function_call, Mapping):
                calls.append(
                    ToolCall(
                        id=str(function_call.get("id", index)),
                        function=FunctionCall(
                            name=str(function_call.get("name", "")),
                            arguments=_tool_arguments(function_call.get("args")),
                        ),
                    )
                )
        return ChatResponse(content="".join(text), tool_calls=calls)


_BACKEND_TYPES: dict[str, type[BaseBackend]] = {
    "chat": ChatBackend,
    "response": ResponseBackend,
    "messages": MessagesBackend,
    "completions": CompletionsBackend,
    "v1beta": V1BetaBackend,
}


class LLMRouter:
    """Route a request to the configured model for its application role."""

    def __init__(self, role_configs: dict[str, Mapping[str, Any]]) -> None:
        self.role_configs = dict(role_configs)
        self._backends: dict[tuple[str, str | None, str], BaseBackend] = {}
        for config in self.role_configs.values():
            self._backend_for(config)

    def _backend_for(self, config: Mapping[str, Any]) -> BaseBackend:
        backend_type = str(config["backend"])
        api_key = config.get("api_key")
        base_url = str(config["base_url"])
        cache_key = (backend_type, api_key if isinstance(api_key, str) else None, base_url.rstrip("/"))
        if cache_key not in self._backends:
            backend_class = _BACKEND_TYPES.get(backend_type)
            if backend_class is None:
                raise ValueError(f"Unsupported LLM backend: {backend_type}")
            self._backends[cache_key] = backend_class(
                api_key=api_key if isinstance(api_key, str) else None,
                base_url=base_url,
                model=str(config["model"]),
            )
        return self._backends[cache_key]

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]] | str,
        tools: Sequence[Mapping[str, Any]] | None = None,
        temperature: float = 0.7,
        role: str = "tool_calling",
    ) -> ChatResponse:
        config = self.role_configs.get(role)
        if config is None:
            return ChatResponse(error=f"No LLM configuration for role: {role}")
        try:
            return await self._backend_for(config).chat(messages, tools, temperature)
        except (KeyError, TypeError, ValueError) as exc:
            return ChatResponse(error=str(exc))


class LLMClient(ResponseBackend):
    """Backward-compatible single-model OpenAI Responses client."""

    def __init__(
        self,
        api_key: str | None,
        base_url: str | None = None,
        model: str = "gpt-4o",
    ) -> None:
        super().__init__(api_key, base_url or PROVIDER_REGISTRY["openai"]["default_base"], model)

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/responses"
