import unittest
from typing import Any, Mapping
from unittest.mock import patch

import httpx

from llm import ChatBackend, DEFAULT_REQUEST_TIMEOUT_SECONDS


class EmptyErrorBackend(ChatBackend):
    async def _post(
        self,
        path: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float | None = None,
    ) -> tuple[Mapping[str, Any] | None, str | None]:
        del timeout
        return None, ""


class LlmBackendTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_backend_normalizes_empty_error_string(self) -> None:
        backend = EmptyErrorBackend(api_key="key", base_url="https://example.invalid", model="model")

        response = await backend.chat("hello")

        self.assertEqual(response.error, "LLM request failed with empty error detail")

    async def test_chat_backend_passes_custom_read_timeout_to_httpx(self) -> None:
        captured: list[httpx.Timeout] = []

        class FakeResponse:
            is_error = False

            def json(self) -> Mapping[str, Any]:
                return {"choices": [{"message": {"content": "ok"}}]}

        class FakeAsyncClient:
            def __init__(self, *, timeout: httpx.Timeout) -> None:
                captured.append(timeout)

            async def __aenter__(self) -> "FakeAsyncClient":
                return self

            async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
                return None

            async def post(
                self,
                url: str,
                json: Mapping[str, Any],
                headers: Mapping[str, str],
            ) -> FakeResponse:
                return FakeResponse()

        backend = ChatBackend(api_key="key", base_url="https://example.invalid", model="model")

        with patch("llm.httpx.AsyncClient", FakeAsyncClient):
            response = await backend.chat("hello", timeout=180.0)

        self.assertEqual(response.content, "ok")
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].read, 180.0)
        self.assertEqual(captured[0].connect, DEFAULT_REQUEST_TIMEOUT_SECONDS)


if __name__ == "__main__":
    unittest.main()
