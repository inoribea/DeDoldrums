import asyncio
import tempfile
import unittest
from unittest import mock

from handler import ResearchHandler
from memory import MemoryStore


class StageGateTests(unittest.TestCase):
    def test_stage_35_advances_after_a_challenge_with_open_issues(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler("Test question", MemoryStore(directory), object())
            handler.stage = 3.5
            handler.adversarial_results = {
                "finding_1": {"status": "needs_revision", "data": {}}
            }
            handler.audit_result = {"passed": True, "gaps": []}

            prompt = asyncio.run(handler.get_stage_prompt())

        self.assertEqual(handler.stage, 4)
        self.assertEqual(handler.gate_credential, {"type": "audit_pass", "detail": "document_audit passed"})
        # Stage 4 no longer returns a peer-review prompt — the adversarial
        # gate is the final quality gate; the loop proceeds directly to the
        # final report generator when it detects stage >= 4.
        self.assertIsNone(prompt)

    def test_stage_35_blocks_without_audit_credential(self) -> None:
        """P8: challenges alone are not enough — no audit pass/downgrade → stay."""
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler("Test question", MemoryStore(directory), object())
            handler.stage = 3.5
            handler.adversarial_results = {"finding_1": {"status": "challenged", "data": {}}}

            prompt = asyncio.run(handler.get_stage_prompt())

        self.assertEqual(handler.stage, 3.5)
        self.assertIsNone(prompt)

    def test_stage_35_blocks_when_audit_failed_without_downgrade(self) -> None:
        """P8: failing audit with no downgrade record → gate stays closed."""
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler("Test question", MemoryStore(directory), object())
            handler.stage = 3.5
            handler.adversarial_results = {"finding_1": {"status": "challenged", "data": {}}}
            handler.audit_result = {
                "passed": False,
                "gaps": ["coverage_complete: 1 个 lens 无产出"],
            }

            prompt = asyncio.run(handler.get_stage_prompt())

        self.assertEqual(handler.stage, 3.5)
        self.assertIsNone(handler.gate_credential)
        self.assertIsNone(prompt)

    def test_stage_35_advances_with_explicit_downgrade_record(self) -> None:
        """P8: failing audit + explicit downgrade → gate opens, reason logged."""
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler("Test question", MemoryStore(directory), object())
            handler.stage = 3.5
            handler.adversarial_results = {"finding_1": {"status": "challenged", "data": {}}}
            handler.audit_result = {
                "passed": False,
                "gaps": ["coverage_complete: 1 个 lens 无产出"],
            }
            handler.gate_credential = {"type": "downgrade", "reason": "经济维度无可靠来源，接受覆盖缺口"}
            handler.open_questions = ["[降级] 经济维度无可靠来源，接受覆盖缺口"]

            prompt = asyncio.run(handler.get_stage_prompt())

        self.assertEqual(handler.stage, 4)
        self.assertEqual(handler.gate_credential["type"], "downgrade")
        self.assertIsNone(prompt)

    async def _run_challenge_and_get_status(
        self, handler: ResearchHandler, challenge_result: dict
    ) -> str:
        """Helper: mock do_challenge, call handler.do_challenge, return status."""
        with mock.patch("handler.do_challenge", return_value=challenge_result):
            await handler.do_challenge(
                {"target": "test finding", "mode": "all"}, None
            )
        return handler.adversarial_results["test finding"]["status"]

    def test_english_clean_verdict_yields_challenged(self) -> None:
        """Structured clean verdict (language-independent) → 'challenged'."""
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler(
                "Test question", MemoryStore(directory), object()
            )
            handler.stage = 3.5

            status = asyncio.run(
                self._run_challenge_and_get_status(
                    handler,
                    {
                        "target": "test finding",
                        "challenges": {
                            "logic_flaw": {
                                "mode": "logic_flaw",
                                "verdict": "clean",
                                "detail": "No substantive issues found.",
                            },
                            "hidden_assumption": {
                                "mode": "hidden_assumption",
                                "verdict": "clean",
                                "detail": "No hidden assumptions detected.",
                            },
                            "missing_evidence": {
                                "mode": "missing_evidence",
                                "verdict": "clean",
                                "detail": "Evidence is sufficient.",
                            },
                            "alternative_explanation": {
                                "mode": "alternative_explanation",
                                "verdict": "clean",
                                "detail": "No better alternative found.",
                            },
                        },
                    },
                )
            )

        self.assertEqual(status, "challenged")

    def test_timeout_returns_inconclusive_not_needs_revision(self) -> None:
        """One mode timed out → 'inconclusive', not 'needs_revision'."""
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler(
                "Test question", MemoryStore(directory), object()
            )
            handler.stage = 3.5

            status = asyncio.run(
                self._run_challenge_and_get_status(
                    handler,
                    {
                        "target": "test finding",
                        "challenges": {
                            "logic_flaw": {
                                "mode": "logic_flaw",
                                "verdict": "clean",
                                "detail": "No logic issues.",
                            },
                            "hidden_assumption": {
                                "mode": "hidden_assumption",
                                "verdict": "inconclusive",
                                "detail": "Challenge timed out after 45s.",
                            },
                        },
                    },
                )
            )

        self.assertEqual(status, "inconclusive")
        self.assertNotEqual(status, "needs_revision")

    def test_issues_found_yields_needs_revision(self) -> None:
        """Structured issues_found verdict → 'needs_revision'."""
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler(
                "Test question", MemoryStore(directory), object()
            )
            handler.stage = 3.5

            status = asyncio.run(
                self._run_challenge_and_get_status(
                    handler,
                    {
                        "target": "test finding",
                        "challenges": {
                            "logic_flaw": {
                                "mode": "logic_flaw",
                                "verdict": "issues_found",
                                "detail": "Circular reasoning detected.",
                            },
                        },
                    },
                )
            )

        self.assertEqual(status, "needs_revision")


if __name__ == "__main__":
    unittest.main()
