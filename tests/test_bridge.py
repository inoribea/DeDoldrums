import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from bridge import ResearchBridge, ResearchSession, _complete_event


class CompleteEventTests(unittest.TestCase):
    def test_complete_event_contains_the_brief_without_execution_findings(self) -> None:
        payload = _complete_event("# Research brief", {"overall": 8})

        self.assertEqual(payload["brief"], "# Research brief")
        self.assertEqual(payload["findings"], [])
        self.assertEqual(payload["confidence"], {"overall": 8})

    def test_completed_run_emits_a_brief_without_terminal_execution_finding(self) -> None:
        async def complete_research(*_: object, **__: object) -> str:
            return "# Research brief"

        memory = Mock()
        handler = SimpleNamespace(
            confidence_scores={"overall": 8},
            findings=[],
            on_status=None,
            on_stage=None,
        )
        with patch("bridge._new_llm_client", return_value=object()), patch(
            "bridge.research_loop", new=complete_research
        ):
            session = ResearchSession("test", "Question", memory=memory)
            session.handler = handler
            ResearchBridge.__new__(ResearchBridge)._run_research(session)

        events = [json.loads(message) for message in session.messages]
        self.assertNotIn("finding", [event["type"] for event in events])
        completed = next(event for event in events if event["type"] == "complete")
        self.assertEqual(completed["brief"], "# Research brief")
        self.assertEqual(completed["findings"], [])
        self.assertEqual(completed["confidence"], {"overall": 8})
        memory.archive_session.assert_called_once_with("Question", [{"final_brief": "# Research brief"}])


if __name__ == "__main__":
    unittest.main()
