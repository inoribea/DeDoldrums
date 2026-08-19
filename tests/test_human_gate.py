"""P4: human checkpoint — pauses after the gate, before the brief, unless
disabled. Never resurrects the deleted peer-review stage (human gate only)."""

import asyncio
import unittest

from agent_loop import research_loop
from llm import ChatResponse


class CheckpointFakeHandler:
    """A handler already past the gate (stage 4) with artifacts to show."""

    stage = 4
    question = "Test question"
    stage_artifacts = {
        "contradiction_map": "矛盾 A vs B",
        "synthesis": "综合结论",
    }
    audit_result = {"passed": True, "gaps": []}
    open_questions: list[str] = []
    memory = None
    findings: list[dict] = []

    async def get_stage_prompt(self) -> None:
        return None


class CheckpointLlmClient:
    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, **kwargs: object) -> ChatResponse:
        self.calls += 1
        if self.calls == 1:
            return ChatResponse(content="Refined question")
        return ChatResponse(content="Final research brief")


class HumanGateTests(unittest.TestCase):
    def test_checkpoint_continue_proceeds_to_brief(self) -> None:
        client = CheckpointLlmClient()
        decisions: list[str] = []

        async def on_checkpoint(handler: object) -> str:
            decisions.append("paused")
            return "continue"

        brief = asyncio.run(research_loop(
            client,
            "Test question",
            handler=CheckpointFakeHandler(),
            human_gate=True,
            on_checkpoint=on_checkpoint,
        ))

        self.assertEqual(brief, "Final research brief")
        self.assertEqual(decisions, ["paused"])

    def test_checkpoint_exit_aborts_before_brief(self) -> None:
        client = CheckpointLlmClient()

        async def on_checkpoint(handler: object) -> str:
            return "exit"

        brief = asyncio.run(research_loop(
            client,
            "Test question",
            handler=CheckpointFakeHandler(),
            human_gate=True,
            on_checkpoint=on_checkpoint,
        ))

        self.assertIn("中止", brief)
        # Only the refinement call — the final brief generator never runs
        self.assertEqual(client.calls, 1)

    def test_checkpoint_feedback_records_open_question(self) -> None:
        client = CheckpointLlmClient()

        async def on_checkpoint(handler: object) -> str:
            handler.open_questions.append("[操作者反馈] 请补充经济维度")
            return "feedback"

        brief = asyncio.run(research_loop(
            client,
            "Test question",
            handler=CheckpointFakeHandler(),
            human_gate=True,
            on_checkpoint=on_checkpoint,
        ))

        self.assertEqual(brief, "Final research brief")

    def test_human_gate_disabled_skips_pause(self) -> None:
        client = CheckpointLlmClient()
        called = False

        async def on_checkpoint(handler: object) -> str:
            nonlocal called
            called = True
            return "continue"

        brief = asyncio.run(research_loop(
            client,
            "Test question",
            handler=CheckpointFakeHandler(),
            human_gate=False,
            on_checkpoint=on_checkpoint,
        ))

        self.assertEqual(brief, "Final research brief")
        self.assertFalse(called)

    def test_no_on_checkpoint_callback_means_no_pause(self) -> None:
        """Backward compat: callers without a callback get the old flow."""
        client = CheckpointLlmClient()

        brief = asyncio.run(research_loop(
            client,
            "Test question",
            handler=CheckpointFakeHandler(),
            human_gate=True,
        ))

        self.assertEqual(brief, "Final research brief")


if __name__ == "__main__":
    unittest.main()
