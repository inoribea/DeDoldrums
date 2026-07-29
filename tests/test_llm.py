import unittest
from typing import Any, Mapping

from llm import ChatBackend


class EmptyErrorBackend(ChatBackend):
    async def _post(
        self,
        path: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
    ) -> tuple[Mapping[str, Any] | None, str | None]:
        return None, ""


class LlmBackendTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_backend_normalizes_empty_error_string(self) -> None:
        backend = EmptyErrorBackend(api_key="key", base_url="https://example.invalid", model="model")

        response = await backend.chat("hello")

        self.assertEqual(response.error, "LLM request failed with empty error detail")


if __name__ == "__main__":
    unittest.main()
