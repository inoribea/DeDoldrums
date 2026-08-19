"""P1: sub_research compression contract.

The main context receives ONLY distilled (claim, source_url, confidence)
triples — never raw sub-agent prose — capped at MAX_SUB_RESULTS_PER_TASK.
"""

import asyncio
import json
import tempfile
import unittest
from unittest import mock

import tools
from llm import ChatResponse
from memory import MemoryStore
from tools import (
    MAX_SUB_RESULTS_PER_TASK,
    _extract_sub_results,
    do_sub_research,
)


def _memory_store() -> MemoryStore:
    return MemoryStore(tempfile.mkdtemp())


class TripleLlmClient:
    """Returns a configurable triple payload per call."""

    def __init__(self, payloads: list[str] | None = None) -> None:
        self.payloads = payloads or [
            json.dumps({"results": [{
                "claim": f"claim {i}",
                "source_url": f"http://example.com/{i}",
                "confidence": "推断",
                "lens": "skeptic",
            }]})
            for i in range(2)
        ]
        self.calls = 0

    async def chat(self, **kwargs: object) -> ChatResponse:
        self.calls += 1
        if self.calls <= len(self.payloads):
            return ChatResponse(content=self.payloads[self.calls - 1])
        return ChatResponse(content=json.dumps({"results": []}))


class ExtractSubResultsTests(unittest.TestCase):
    def test_bare_json_parses(self) -> None:
        raw = json.dumps({"results": [{
            "claim": "c", "source_url": "u", "confidence": "已知", "lens": "l",
        }]})
        results, error = _extract_sub_results(raw, "skeptic", "怀疑论者")
        self.assertIsNone(error)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["claim"], "c")

    def test_fenced_json_parses(self) -> None:
        raw = '```json\n{"results": [{"claim": "c", "source_url": "u", "confidence": "猜测", "lens": "l"}]}\n```'
        results, error = _extract_sub_results(raw, "skeptic", "怀疑论者")
        self.assertIsNone(error)
        self.assertEqual(len(results), 1)

    def test_inline_objects_recovered_from_prose(self) -> None:
        raw = '分析如下 {"claim": "内嵌对象", "source_url": "u", "confidence": "推断"}'
        results, error = _extract_sub_results(raw, "skeptic", "怀疑论者")
        self.assertIsNone(error)
        self.assertEqual(results[0]["claim"], "内嵌对象")

    def test_garbage_returns_error_and_no_results(self) -> None:
        results, error = _extract_sub_results("完全不是 JSON 的散文", "skeptic", "怀疑论者")
        self.assertEqual(results, [])
        self.assertIsNotNone(error)

    def test_missing_claim_entries_are_dropped(self) -> None:
        raw = json.dumps({"results": [
            {"claim": "  ", "source_url": "u", "confidence": "已知"},
            {"claim": "valid", "source_url": "u2", "confidence": "已知"},
        ]})
        results, error = _extract_sub_results(raw, "skeptic", "怀疑论者")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["claim"], "valid")

    def test_cap_at_max_triples(self) -> None:
        many = [{"claim": f"c{i}", "source_url": f"u{i}", "confidence": "猜测"} for i in range(30)]
        raw = json.dumps({"results": many})
        results, error = _extract_sub_results(raw, "skeptic", "怀疑论者")
        self.assertLessEqual(len(results), MAX_SUB_RESULTS_PER_TASK)


class CompressionContractTests(unittest.TestCase):
    def test_main_context_contains_only_triples(self) -> None:
        client = TripleLlmClient()
        tasks = [{"lens": "skeptic", "question": "q1"}, {"lens": "practitioner", "question": "q2"}]

        with mock.patch("tools.web_search", return_value=[]):
            result = asyncio.run(do_sub_research(tasks, client, _memory_store()))

        aggregated = result["aggregated"]
        self.assertIn("claim 0", aggregated)
        self.assertIn("claim 1", aggregated)
        # No raw prose, no search-process chatter
        self.assertNotIn("```", aggregated)
        self.assertNotIn("搜索过程", aggregated)

    def test_fan_out_still_concurrent(self) -> None:
        client = TripleLlmClient()
        tasks = [{"lens": "skeptic", "question": "q1"}, {"lens": "practitioner", "question": "q2"}]

        with mock.patch("tools.web_search", return_value=[]):
            result = asyncio.run(do_sub_research(tasks, client, _memory_store()))

        self.assertEqual(len(result["task_results"]), 2)
        for task_result in result["task_results"]:
            self.assertIn("results", task_result)
            self.assertTrue(all(
                set(t) >= {"claim", "source_url", "confidence"} for t in task_result["results"]
            ))

    def test_distilled_output_is_json_serializable(self) -> None:
        client = TripleLlmClient()
        tasks = [{"lens": "skeptic", "question": "q1"}]

        with mock.patch("tools.web_search", return_value=[]):
            result = asyncio.run(do_sub_research(tasks, client, _memory_store()))

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn("claim 0", serialized)


if __name__ == "__main__":
    unittest.main()
