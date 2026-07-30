import asyncio
import json
import tempfile
import unittest
from unittest import mock

import tools
from handler import ResearchHandler
from llm import ChatResponse
from memory import MemoryStore
from tools import (
    MAX_SUB_RESULT_CHARS,
    SUB_RESEARCH_TIMEOUT_SECONDS,
    do_sub_research,
)


def _memory_store() -> MemoryStore:
    return MemoryStore(tempfile.mkdtemp())


class CountingLlmClient:
    """Tracks concurrent calls to verify fan-out parallelism."""

    def __init__(self, response_text: str = "Analysis result") -> None:
        self.active = 0
        self.max_active = 0
        self.calls = 0
        self.response_text = response_text

    async def chat(self, **kwargs: object) -> ChatResponse:
        self.calls += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.01)
            return ChatResponse(content=self.response_text)
        finally:
            self.active -= 1


class FailingLlmClient:
    """Returns an error for the second call, succeeds on others."""

    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, **kwargs: object) -> ChatResponse:
        self.calls += 1
        if self.calls == 2:
            return ChatResponse(error="simulated backend failure")
        return ChatResponse(content="Analysis result")


class HangingLlmClient:
    """Sleeps beyond the timeout — triggers asyncio.wait_for TimeoutError."""

    async def chat(self, **kwargs: object) -> ChatResponse:
        await asyncio.sleep(SUB_RESEARCH_TIMEOUT_SECONDS + 0.5)
        return ChatResponse(content="too late")


class LongResultLlmClient:
    """Returns a result far exceeding the truncation cap."""

    async def chat(self, **kwargs: object) -> ChatResponse:
        return ChatResponse(content="x" * (MAX_SUB_RESULT_CHARS * 10))


def _make_tasks(n: int = 3) -> list[dict[str, str]]:
    return [
        {"lens": "skeptic", "question": "What are the risks?"},
        {"lens": "practitioner", "question": "How does it work in practice?"},
        {"lens": "academic", "question": "What does the research say?"},
    ][:n]


class SubResearchToolTests(unittest.TestCase):
    """Module-level ``do_sub_research`` tests."""

    def test_three_tasks_fan_out_concurrently(self) -> None:
        client = CountingLlmClient()
        tasks = _make_tasks(3)

        with mock.patch("tools.web_search", return_value=[]):
            result = asyncio.run(do_sub_research(tasks, client, _memory_store()))

        self.assertEqual(client.calls, 3)
        self.assertGreater(client.max_active, 1)
        self.assertEqual(len(result["task_results"]), 3)
        self.assertIn("aggregated", result)

    def test_exception_normalization_produces_json_safe_output(self) -> None:
        client = FailingLlmClient()
        tasks = _make_tasks(3)

        with mock.patch("tools.web_search", return_value=[]):
            result = asyncio.run(do_sub_research(tasks, client, _memory_store()))

        # The second task should have an error in its summary
        self.assertEqual(len(result["task_results"]), 3)
        self.assertIn("LLM error", result["task_results"][1]["summary"])

        # json.dumps must not raise TypeError
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("simulated backend failure", serialized)

    def test_sub_agent_timeout_returns_error_entry(self) -> None:
        original_timeout = tools.SUB_RESEARCH_TIMEOUT_SECONDS
        tools.SUB_RESEARCH_TIMEOUT_SECONDS = 0.01
        try:
            client = HangingLlmClient()
            tasks = _make_tasks(1)

            with mock.patch("tools.web_search", return_value=[]):
                result = asyncio.run(do_sub_research(tasks, client, _memory_store()))

            self.assertEqual(len(result["task_results"]), 1)
            self.assertIn("timed out", result["task_results"][0]["error"])
        finally:
            tools.SUB_RESEARCH_TIMEOUT_SECONDS = original_timeout

    def test_long_result_is_truncated_to_cap(self) -> None:
        client = LongResultLlmClient()
        tasks = _make_tasks(1)

        with mock.patch("tools.web_search", return_value=[]):
            result = asyncio.run(do_sub_research(tasks, client, _memory_store()))

        self.assertEqual(len(result["task_results"]), 1)
        summary = result["task_results"][0]["summary"]
        self.assertLessEqual(len(summary), MAX_SUB_RESULT_CHARS)

    def test_unknown_lens_returns_error(self) -> None:
        client = CountingLlmClient()
        tasks = [{"lens": "nonexistent_lens", "question": "Test"}]

        with mock.patch("tools.web_search", return_value=[]):
            result = asyncio.run(do_sub_research(tasks, client, _memory_store()))

        self.assertEqual(len(result["task_results"]), 1)
        self.assertIn("Unknown lens", result["task_results"][0]["error"])

    def test_empty_tasks_returns_error(self) -> None:
        client = CountingLlmClient()

        result = asyncio.run(do_sub_research([], client, _memory_store()))

        self.assertEqual(result["task_results"], [])
        self.assertIn("error", result)


class HandlerSubResearchTests(unittest.TestCase):
    """``ResearchHandler.do_sub_research`` integration tests."""

    def test_lenses_used_is_populated_for_stage_one_gate(self) -> None:
        handler = ResearchHandler("Test question", _memory_store(), CountingLlmClient())
        handler.stage = 1

        tasks = _make_tasks(3)
        args = {"tasks": tasks}

        with mock.patch("tools.web_search", return_value=[]):
            outcome = asyncio.run(handler.do_sub_research(args, None))

        self.assertEqual(len(handler.lenses_used), 3)
        self.assertIn("skeptic", handler.lenses_used)
        self.assertIn("practitioner", handler.lenses_used)
        self.assertIn("academic", handler.lenses_used)
        self.assertEqual(len(handler.findings), 1)
        self.assertIsNone(outcome.next_prompt)
        self.assertFalse(outcome.should_exit)

    def test_missing_tasks_returns_error(self) -> None:
        handler = ResearchHandler("Test question", _memory_store(), CountingLlmClient())

        outcome = asyncio.run(handler.do_sub_research({}, None))

        self.assertIn("error", outcome.data)
        self.assertEqual(len(handler.lenses_used), 0)


class ChallengeRaceRegressionTests(unittest.TestCase):
    """Verify the ``finding_N`` race fix: two concurrent challenges
    with ``target=""`` must produce distinct keys in ``adversarial_results``."""

    def test_concurrent_anonymous_challenges_do_not_collide(self) -> None:
        handler = ResearchHandler("Test question", _memory_store(), CountingLlmClient())
        handler.stage = 3.5

        async def _run_two() -> None:
            await asyncio.gather(
                handler.do_challenge({"target": "", "mode": "logic_flaw"}, None),
                handler.do_challenge({"target": "", "mode": "hidden_assumption"}, None),
            )

        asyncio.run(_run_two())

        self.assertEqual(len(handler.adversarial_results), 2)
        keys = list(handler.adversarial_results)
        self.assertNotEqual(keys[0], keys[1])


class LensDiscoveryLanguageTests(unittest.TestCase):
    """Verify lens gap detection works with English LLM output."""

    def test_english_dimension_field_produces_coverage(self) -> None:
        """Lenses with English identity/concerns but valid dimension → no false gaps."""
        from lenses import _find_gaps

        english_lenses = [
            {
                "key": "policy_maker",
                "name": "Policy Maker",
                "identity": "You shape the rules others must follow.",
                "concerns": "regulatory impact, enforcement, unintended consequences",
                "blind_spot": "May overlook practical implementation friction",
                "dimension": "other",
            },
            {
                "key": "industry_critic",
                "name": "Industry Critic",
                "identity": "You believe industry claims are systematically inflated.",
                "concerns": "conflicts of interest, survivorship bias, suppressed evidence",
                "blind_spot": "May dismiss genuine progress",
                "dimension": "skeptic",
            },
            {
                "key": "field_practitioner",
                "name": "Field Practitioner",
                "identity": "You deal with this on the ground every day.",
                "concerns": "actual usability, hidden costs, common failure modes",
                "blind_spot": "May overlook theoretical breakthroughs",
                "dimension": "practitioner",
            },
        ]

        gaps = _find_gaps(english_lenses)
        # Only academic is uncovered — practitioner and skeptic are covered
        self.assertEqual(gaps, ["academic"])

    def test_chinese_legacy_fallback_still_works(self) -> None:
        """Lenses without dimension field → legacy Chinese keyword fallback."""
        from lenses import _find_gaps

        chinese_legacy_lenses = [
            {
                "key": "prac",
                "name": "从业者",
                "identity": "你是一个每天与这个话题打交道的从业者。",
                "concerns": "实际操作中的坑和隐性成本",
                "blind_spot": "容易忽视理论突破",
                # No dimension field — legacy fallback
            },
        ]

        gaps = _find_gaps(chinese_legacy_lenses)
        # Legacy keyword match: "从业" + "每天" → practitioner
        # skeptic and academic should be missing
        self.assertNotIn("practitioner", gaps)
        self.assertIn("skeptic", gaps)
        self.assertIn("academic", gaps)


if __name__ == "__main__":
    unittest.main()
