"""P2: document-level audit — five rubric items, catches
'logically fine but coverage-poor' documents that challenge alone misses."""

import asyncio
import tempfile
import unittest
from unittest import mock

from handler import ResearchHandler
from llm import ChatResponse
from memory import MemoryStore
from tools import audit_document


class AuditLlmClient:
    """Stubbed content-review role returning configurable verdict lines."""

    def __init__(self, text: str = "COUNTEREVIDENCE: PASS — 有反例\nBLIND_SPOTS: PASS — 具体缺口") -> None:
        self.text = text
        self.calls = 0

    async def chat(self, **kwargs: object) -> ChatResponse:
        self.calls += 1
        return ChatResponse(content=self.text)


def _findings() -> list[dict]:
    return [
        {"claim": "f1", "source_url": "http://a.example", "confidence": "已知", "lens": "skeptic"},
        {"claim": "f2", "source_url": "http://b.example", "confidence": "推断", "lens": "practitioner"},
        {"claim": "f3", "source_url": "http://c.example", "confidence": "猜测", "lens": "academic"},
    ]


def _artifacts() -> dict[str, str]:
    return {
        "contradiction_map": "视角 A 与 B 直接矛盾：A 认为 X，B 认为 Y。证据力度对比…",
        "synthesis": "摘要…\n\n## Blind Spots\n- 搜过英语来源，未检索非英语语料\n- 未访谈实践者 [可能不全]",
    }


class AuditRubricTests(unittest.TestCase):
    def test_pass_when_document_is_sound(self) -> None:
        result = asyncio.run(audit_document(
            _findings(),
            {"skeptic", "practitioner", "academic"},
            [{"key": "skeptic"}, {"key": "practitioner"}, {"key": "academic"}],
            _artifacts(),
            AuditLlmClient(),
        ))
        self.assertTrue(result["passed"], result["gaps"])
        self.assertEqual(result["gaps"], [])

    def test_fails_when_coverage_is_incomplete(self) -> None:
        """A document that is logically fine but misses a lens must FAIL."""
        findings = _findings()[:2]  # no academic finding — academic lens unused
        result = asyncio.run(audit_document(
            findings,
            {"skeptic", "practitioner"},  # academic never used
            [{"key": "skeptic"}, {"key": "practitioner"}, {"key": "academic"}],
            _artifacts(),
            AuditLlmClient(),
        ))
        self.assertFalse(result["passed"])
        self.assertTrue(any("coverage_complete" in gap for gap in result["gaps"]))

    def test_fails_when_sources_missing(self) -> None:
        findings = _findings()
        findings.append({"claim": "f4", "source_url": "", "confidence": "猜测", "lens": "historian"})
        result = asyncio.run(audit_document(
            findings,
            {"skeptic", "practitioner", "academic", "historian"},
            [{"key": k} for k in ("skeptic", "practitioner", "academic", "historian")],
            _artifacts(),
            AuditLlmClient(),
        ))
        self.assertFalse(result["passed"])
        self.assertTrue(any("source_locatable" in gap for gap in result["gaps"]))

    def test_fails_when_blind_spots_are_platitudes(self) -> None:
        artifacts = dict(_artifacts())
        artifacts["synthesis"] = "摘要…\n\n## Blind Spots\n需要更多研究。"
        result = asyncio.run(audit_document(
            _findings(),
            {"skeptic", "practitioner", "academic"},
            [{"key": k} for k in ("skeptic", "practitioner", "academic")],
            artifacts,
            AuditLlmClient(text="COUNTEREVIDENCE: PASS — 有反例\nBLIND_SPOTS: FAIL — 只有空话"),
        ))
        self.assertFalse(result["passed"])
        self.assertTrue(any("honest_blind_spots" in gap for gap in result["gaps"]))

    def test_fails_when_synthesis_missing_blind_spots_section(self) -> None:
        artifacts = dict(_artifacts())
        artifacts["synthesis"] = "摘要…（覆盖了主要来源，未检索非英语语料）"
        result = asyncio.run(audit_document(
            _findings(),
            {"skeptic", "practitioner", "academic"},
            [{"key": k} for k in ("skeptic", "practitioner", "academic")],
            artifacts,
            AuditLlmClient(text="COUNTEREVIDENCE: PASS — 有反例\nBLIND_SPOTS: PASS — 看起来诚实"),
        ))
        # Deterministic supplement: no Blind Spots heading → forced FAIL
        self.assertFalse(result["passed"])
        self.assertTrue(any("honest_blind_spots" in gap for gap in result["gaps"]))

    def test_fails_when_known_label_has_no_source(self) -> None:
        findings = [
            {"claim": "x", "source_url": "", "confidence": "已知", "lens": "skeptic"},
        ]
        result = asyncio.run(audit_document(
            findings,
            {"skeptic"},
            [{"key": "skeptic"}],
            _artifacts(),
            AuditLlmClient(),
        ))
        self.assertFalse(result["passed"])
        self.assertTrue(any("labels_correct" in gap for gap in result["gaps"]))

    def test_llm_failure_degrades_to_failing_items_not_crash(self) -> None:
        class ExplodingLlmClient:
            async def chat(self, **kwargs: object) -> ChatResponse:
                raise RuntimeError("backend down")

        result = asyncio.run(audit_document(
            _findings(),
            {"skeptic", "practitioner", "academic"},
            [{"key": k} for k in ("skeptic", "practitioner", "academic")],
            _artifacts(),
            ExplodingLlmClient(),
        ))
        self.assertFalse(result["passed"])
        self.assertIn("passed", result)


class HandlerAuditTests(unittest.TestCase):
    def test_do_document_audit_records_result_and_pass_credential(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler("Q", MemoryStore(directory), AuditLlmClient())
            handler.stage_artifacts = dict(_artifacts())
            handler.lenses_used = {"skeptic", "practitioner", "academic"}
            handler.dynamic_lenses = [{"key": k} for k in ("skeptic", "practitioner", "academic")]
            for finding in _findings():
                handler._append_finding(finding)

            outcome = asyncio.run(handler.do_document_audit({}, None))

            self.assertIsNotNone(handler.audit_result)
            self.assertEqual(handler.gate_credential, {"type": "audit_pass", "detail": "document_audit passed"})
            self.assertIn("passed", outcome.data)

    def test_downgrade_note_opens_gate_and_logs_question(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler("Q", MemoryStore(directory), AuditLlmClient())
            handler.stage_artifacts = {}
            handler.lenses_used = {"skeptic"}
            handler.dynamic_lenses = [{"key": "skeptic"}, {"key": "academic"}]
            handler._append_finding({"claim": "x", "source_url": "http://a.example", "confidence": "已知", "lens": "skeptic"})

            outcome = asyncio.run(handler.do_document_audit(
                {"downgrade_note": "学术视角无可靠来源，接受覆盖缺口"}, None
            ))

            self.assertEqual(handler.gate_credential["type"], "downgrade")
            self.assertTrue(handler.open_questions)
            self.assertIn("降级", handler.open_questions[0])
            self.assertTrue(outcome.data.get("downgrade_recorded"))


if __name__ == "__main__":
    unittest.main()
