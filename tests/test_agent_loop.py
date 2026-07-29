import asyncio
import json
import os
import tempfile
import unittest

from agent_loop import research_loop
from llm import ChatResponse, FunctionCall, ToolCall
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
        self.calls: list[tuple[object, object]] = []

    async def chat(self, **kwargs: object) -> ChatResponse:
        messages = kwargs.get("messages")
        if isinstance(messages, list):
            self.requests.append(list(messages))
        self.calls.append((kwargs.get("tools"), kwargs.get("role")))
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
        self.assertEqual(client.calls[1], ([], "tool_calling"))
        self.assertEqual(client.calls[2], ([], "conversational"))

    def test_final_peer_review_rejects_tool_calls(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(tool_calls=[ToolCall(
                id="unexpected-tool",
                function=FunctionCall(name="challenge", arguments="{}"),
            )]),
        ])

        with self.assertRaisesRegex(RuntimeError, "unexpected tool calls"):
            asyncio.run(research_loop(client, "Test question", handler=FinalReviewHandler()))

        self.assertEqual(client.calls[1], ([], "tool_calling"))

    def test_empty_final_peer_review_raises(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="   "),
        ])

        with self.assertRaisesRegex(RuntimeError, "peer review was empty"):
            asyncio.run(research_loop(client, "Test question", handler=FinalReviewHandler()))

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

    def test_empty_final_brief_after_retries_returns_recovered_brief(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="Peer review"),
            ChatResponse(content="   "),
            ChatResponse(content=""),
            ChatResponse(content=""),
        ])

        brief = asyncio.run(research_loop(client, "Test question", handler=FinalReviewHandler()))

        self.assertIn("Research brief (recovered)", brief)
        self.assertIn("Peer review", brief)

    def test_empty_api_response_after_retries_returns_recovered_brief(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="Peer review"),
            ChatResponse(error="Empty API response"),
            ChatResponse(error="Empty API response"),
            ChatResponse(error="Empty API response"),
        ])

        brief = asyncio.run(research_loop(client, "Test question", handler=FinalReviewHandler()))

        self.assertIn("Research brief (recovered)", brief)
        self.assertIn("Failure reason: Empty API response", brief)
        self.assertIn("Peer review", brief)

    def test_final_brief_error_retry_succeeds(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="Peer review"),
            ChatResponse(error="transient error"),
            ChatResponse(content="Recovered final research brief"),
        ])

        brief = asyncio.run(research_loop(client, "Test question", handler=FinalReviewHandler()))
        self.assertEqual(brief, "Recovered final research brief")

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
