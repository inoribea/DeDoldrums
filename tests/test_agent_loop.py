import asyncio
import json
import os
import tempfile
import unittest

from agent_loop import research_loop
from llm import ChatResponse
from memory import MemoryStore
from tools import do_crystallize


class FakeHandler:
    stage = 0
    findings: list[dict[str, str]] = []

    async def get_stage_prompt(self) -> None:
        return None


class FinalReviewHandler(FakeHandler):
    stage = 4
    findings = [{"type": "reflection", "data": {}}]


class FakeLlmClient:
    def __init__(self, responses: list[ChatResponse]) -> None:
        self.responses = iter(responses)
        self.requests: list[list[dict[str, object]]] = []

    async def chat(self, **kwargs: object) -> ChatResponse:
        messages = kwargs.get("messages")
        if isinstance(messages, list):
            self.requests.append(list(messages))
        return next(self.responses)


class ResearchLoopTests(unittest.TestCase):
    def test_peer_review_response_is_included_in_final_report_context(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="Peer review: revise the timeline claim."),
            ChatResponse(content="Final research brief"),
        ])

        brief = asyncio.run(research_loop(client, "Test question", handler=FinalReviewHandler()))

        self.assertEqual(brief, "Final research brief")
        final_request = client.requests[-1]
        self.assertTrue(
            any(
                message.get("role") == "assistant"
                and message.get("content") == "Peer review: revise the timeline claim."
                for message in final_request
            )
        )

    def test_empty_final_brief_retries_once(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="Peer review"),
            ChatResponse(content=""),
            ChatResponse(content="Recovered final research brief"),
        ])

        brief = asyncio.run(research_loop(client, "Test question", handler=FinalReviewHandler()))

        self.assertEqual(brief, "Recovered final research brief")
        self.assertEqual(len(client.requests), 4)

    def test_empty_final_brief_after_retry_raises(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="Peer review"),
            ChatResponse(content="   "),
            ChatResponse(content=""),
        ])

        with self.assertRaisesRegex(RuntimeError, "empty after retry"):
            asyncio.run(research_loop(client, "Test question", handler=FinalReviewHandler()))

    def test_final_brief_error_raises(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="Peer review"),
            ChatResponse(error="provider unavailable"),
        ])

        with self.assertRaisesRegex(RuntimeError, "Final research brief failed"):
            asyncio.run(research_loop(client, "Test question", handler=FinalReviewHandler()))

    def test_thinking_pattern_crystallization_persists_sop_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = MemoryStore(directory)
            result = asyncio.run(do_crystallize({
                "category": "thinking_pattern",
                "insight": "Compare independent resource estimates.",
                "trigger_condition": "Assessing quantum timelines",
            }, memory))

            self.assertEqual(result["crystallized"], "thinking_pattern")
            with open(os.path.join(directory, "L3_thinking_sops", "patterns.md"), encoding="utf-8") as file:
                self.assertIn("Compare independent resource estimates.", file.read())
            with open(os.path.join(directory, "L1_pattern_index.json"), encoding="utf-8") as file:
                index = json.load(file)
            self.assertTrue(index)

    def test_model_error_terminates_the_session(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(error="upstream timeout"),
        ])

        with self.assertRaisesRegex(RuntimeError, "Research model request failed"):
            asyncio.run(research_loop(client, "Test question", handler=FakeHandler()))

    def test_repeated_no_tool_responses_terminate_the_session(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="I will consider the problem."),
            ChatResponse(content="Still considering."),
            ChatResponse(content="One more thought."),
        ])

        with self.assertRaisesRegex(RuntimeError, "stopped issuing tool calls"):
            asyncio.run(research_loop(client, "Test question", handler=FakeHandler()))


if __name__ == "__main__":
    unittest.main()
