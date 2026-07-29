import asyncio
import json
import os
import tempfile
import unittest

from agent_loop import (
    FINAL_REPORT_CONTEXT_MAX_CHARS,
    FINAL_REPORT_RETRY_PROMPT,
    FINAL_SYNTHESIS_TIMEOUT_SECONDS,
    _compact_final_report_messages,
    _fallback_final_brief,
    _no_tool_retry_prompt,
    research_loop,
)
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


class StageOneHandler(FakeHandler):
    stage = 1
    lenses_used = {"skeptic"}
    dynamic_lenses = [
        {"key": "skeptic", "name": "Skeptic"},
        {"key": "practitioner", "name": "Practitioner"},
        {"key": "academic", "name": "Academic"},
    ]


class StageThreePointFiveHandler(FakeHandler):
    stage = 3.5
    adversarial_results: dict[str, object] = {}


class FakeLlmClient:
    def __init__(self, responses: list[ChatResponse]) -> None:
        self.responses = iter(responses)
        self.requests: list[list[dict[str, object]]] = []
        self.calls: list[tuple[object, object]] = []
        self.kwargs: list[dict[str, object]] = []

    async def chat(self, **kwargs: object) -> ChatResponse:
        self.kwargs.append(dict(kwargs))
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

    def test_final_synthesis_calls_use_extended_timeout(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="Peer review"),
            ChatResponse(content="Final research brief"),
        ])

        brief = asyncio.run(research_loop(client, "Test question", handler=FinalReviewHandler()))

        self.assertEqual(brief, "Final research brief")
        self.assertIsNone(client.kwargs[0].get("timeout"))
        self.assertEqual(client.kwargs[1].get("timeout"), FINAL_SYNTHESIS_TIMEOUT_SECONDS)
        self.assertEqual(client.kwargs[2].get("timeout"), FINAL_SYNTHESIS_TIMEOUT_SECONDS)

    def test_final_brief_error_retry_does_not_grow_payload(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="Peer review"),
            ChatResponse(error="The read operation timed out"),
            ChatResponse(error="The read operation timed out"),
            ChatResponse(error="The read operation timed out"),
        ])

        brief = asyncio.run(research_loop(client, "Test question", handler=FinalReviewHandler()))

        self.assertIn("Research brief (recovered)", brief)
        final_requests = client.requests[2:]
        self.assertEqual(len(final_requests), 3)
        self.assertEqual([len(request) for request in final_requests], [4, 4, 4])
        self.assertFalse(any(
            message.get("content") == FINAL_REPORT_RETRY_PROMPT
            for request in final_requests
            for message in request
        ))

    def test_empty_final_brief_retry_prompt_stays_local_to_final_request(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="Peer review"),
            ChatResponse(content=""),
            ChatResponse(content="Recovered final research brief"),
        ])

        brief = asyncio.run(research_loop(client, "Test question", handler=FinalReviewHandler()))

        self.assertEqual(brief, "Recovered final research brief")
        self.assertTrue(any(
            message.get("content") == FINAL_REPORT_RETRY_PROMPT
            for message in client.requests[-1]
        ))

    def test_final_report_context_is_capped_by_character_budget(self) -> None:
        messages = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "question"},
            {"role": "assistant", "content": "old note should be dropped"},
            {"role": "assistant", "content": "new" * FINAL_REPORT_CONTEXT_MAX_CHARS},
        ]

        compact = _compact_final_report_messages(messages)
        serialized_size = sum(len(json.dumps(message, ensure_ascii=False)) for message in compact)

        self.assertLessEqual(serialized_size, FINAL_REPORT_CONTEXT_MAX_CHARS)
        self.assertEqual(compact[0]["role"], "system")
        self.assertEqual(compact[1]["role"], "user")
        self.assertIn("truncated", str(compact[-1].get("content")))

    def test_recovered_brief_removes_tool_call_markup(self) -> None:
        brief = _fallback_final_brief([
            {"role": "system", "content": "secret system prompt"},
            {"role": "user", "content": "question"},
            {
                "role": "assistant",
                "content": (
                    "Readable synthesis\n"
                    "<｜｜DSML｜｜tool_calls>"
                    "<｜｜DSML｜｜invoke name=\"challenge\">machine payload"
                    "</｜｜DSML｜｜tool_calls>"
                ),
            },
        ], "Empty API response")

        self.assertIn("Readable synthesis", brief)
        self.assertNotIn("DSML", brief)
        self.assertNotIn("tool_calls", brief)
        self.assertNotIn("secret system prompt", brief)

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

    def test_stage_one_no_tool_retry_prompt_names_reflect(self) -> None:
        prompt = _no_tool_retry_prompt(StageOneHandler())

        self.assertIn("reflect", prompt)
        self.assertIn("1/3", prompt)
        self.assertIn("practitioner", prompt)

    def test_stage_35_no_tool_retry_prompt_names_challenge_gate(self) -> None:
        prompt = _no_tool_retry_prompt(StageThreePointFiveHandler())

        self.assertIn("challenge", prompt)
        self.assertIn("adversarial gate", prompt)
        self.assertIn("Plain-text", prompt)

    def test_no_tool_retry_uses_stage_aware_prompt_in_loop(self) -> None:
        client = FakeLlmClient([
            ChatResponse(content="Refined question"),
            ChatResponse(content="I will describe the adversarial review in prose."),
            ChatResponse(content="Still no tool call."),
            ChatResponse(content="One more prose response."),
        ])

        with self.assertRaisesRegex(RuntimeError, "stopped issuing tool calls"):
            asyncio.run(research_loop(client, "Test question", handler=StageThreePointFiveHandler()))

        retry_request = client.requests[2]
        self.assertTrue(any(
            isinstance(message.get("content"), str)
            and "challenge tool" in message["content"]
            for message in retry_request
        ))


if __name__ == "__main__":
    unittest.main()
