import asyncio
import unittest
from unittest import mock

import tools
from llm import ChatResponse
from tools import _output_directive, do_challenge, do_sub_research


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

    def test_challenge_timeout_returns_inconclusive_verdict(self) -> None:
        original_timeout = tools.CHALLENGE_TIMEOUT_SECONDS
        tools.CHALLENGE_TIMEOUT_SECONDS = 0.01
        try:
            result = asyncio.run(do_challenge({"target": "Claim", "mode": "logic_flaw"}, HangingLlmClient()))
        finally:
            tools.CHALLENGE_TIMEOUT_SECONDS = original_timeout

        verdict = result["challenges"]["logic_flaw"]
        self.assertIsInstance(verdict, dict)
        self.assertEqual(verdict["verdict"], "inconclusive")
        self.assertIn("timed out", verdict["detail"])

    def test_challenge_with_skeleton_adds_extraction_call(self) -> None:
        """skeleton=True strips the claim via a separate extraction call before
        the challenger sees it, and marks the result as skeletonized."""
        client = ConcurrentLlmClient()

        result = asyncio.run(
            do_challenge({"target": "Claim", "mode": "logic_flaw", "skeleton": True}, client)
        )

        # 1 skeleton extraction (role=creative) + 1 challenge (role=content_review)
        self.assertEqual(client.calls, 2)
        self.assertTrue(result["skeletonized"])
        self.assertFalse(result["grounded"])

    def test_challenge_with_grounding_retrieves_sources(self) -> None:
        """grounding=True retrieves external sources before challenging and
        marks the result as grounded."""
        client = ConcurrentLlmClient()

        with mock.patch(
            "tools.web_search",
            return_value=[{"title": "T", "url": "http://example.com", "snippet": "S"}],
        ) as search:
            result = asyncio.run(
                do_challenge({"target": "Claim", "mode": "logic_flaw", "grounding": True}, client)
            )

        search.assert_called_once()
        self.assertTrue(result["grounded"])
        self.assertFalse(result["skeletonized"])

    def test_challenge_defaults_to_no_decorrelation(self) -> None:
        """Backwards compatibility: without skeleton/grounding, no extra calls."""
        client = ConcurrentLlmClient()

        result = asyncio.run(do_challenge({"target": "Claim", "mode": "logic_flaw"}, client))

        self.assertEqual(client.calls, 1)
        self.assertFalse(result["skeletonized"])
        self.assertFalse(result["grounded"])


class OutputLanguageTests(unittest.TestCase):
    """Verify sub-agent and final-report output language contracts."""

    def test_output_directive_en(self) -> None:
        self.assertIn("English", _output_directive("en"))
        self.assertNotIn("中文", _output_directive("en"))

    def test_output_directive_zh_default(self) -> None:
        self.assertIn("中文", _output_directive("zh"))
        self.assertIn("中文", _output_directive(None))

    def test_sub_research_en_language_contract(self) -> None:
        """do_sub_research with report_language='en' emits English prompt."""
        client = ConcurrentLlmClient()
        tasks = [{"lens": "skeptic", "question": "Test"}]

        with mock.patch("tools.web_search", return_value=[]):
            result = asyncio.run(
                do_sub_research(tasks, client, _memory_store(), report_language="en")
            )

        self.assertIn("task_results", result)
        self.assertNotIn("使用中文", str(result))

    def test_sub_research_zh_default_contract(self) -> None:
        """do_sub_research without report_language defaults to Chinese."""
        client = ConcurrentLlmClient()
        tasks = [{"lens": "skeptic", "question": "Test"}]

        with mock.patch("tools.web_search", return_value=[]):
            result = asyncio.run(
                do_sub_research(tasks, client, _memory_store())
            )

        self.assertIn("task_results", result)


def _memory_store():
    import tempfile
    from memory import MemoryStore
    return MemoryStore(tempfile.mkdtemp())


if __name__ == "__main__":
    unittest.main()
