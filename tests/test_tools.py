import asyncio
import unittest

import tools
from llm import ChatResponse
from tools import do_challenge


class ConcurrentLlmClient:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.calls = 0

    async def chat(self, **kwargs: object) -> ChatResponse:
        self.calls += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.01)
            return ChatResponse(content="没问题")
        finally:
            self.active -= 1


class HangingLlmClient:
    async def chat(self, **kwargs: object) -> ChatResponse:
        await asyncio.sleep(1)
        return ChatResponse(content="too late")


class ChallengeToolTests(unittest.TestCase):
    def test_all_challenge_modes_run_concurrently(self) -> None:
        client = ConcurrentLlmClient()

        result = asyncio.run(do_challenge({"target": "Claim", "mode": "all"}, client))

        self.assertEqual(client.calls, 4)
        self.assertGreater(client.max_active, 1)
        self.assertEqual(
            set(result["challenges"]),
            {
                "logic_flaw",
                "hidden_assumption",
                "missing_evidence",
                "alternative_explanation",
            },
        )

    def test_challenge_timeout_returns_a_result(self) -> None:
        original_timeout = tools.CHALLENGE_TIMEOUT_SECONDS
        tools.CHALLENGE_TIMEOUT_SECONDS = 0.01
        try:
            result = asyncio.run(do_challenge({"target": "Claim", "mode": "logic_flaw"}, HangingLlmClient()))
        finally:
            tools.CHALLENGE_TIMEOUT_SECONDS = original_timeout

        self.assertIn("timed out", result["challenges"]["logic_flaw"])


if __name__ == "__main__":
    unittest.main()
