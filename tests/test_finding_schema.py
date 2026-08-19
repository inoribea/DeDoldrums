"""P5: findings schema enforcement — every claim-carrying finding must carry
source_url + confidence, downgrading to 猜测 when a source is missing."""

import asyncio
import tempfile
import unittest

from handler import ResearchHandler
from memory import MemoryStore
from tools import (
    CONFIDENCE_GUESS,
    CONFIDENCE_KNOWN,
    CONFIDENCE_LEVELS,
    validate_finding,
)


class ValidateFindingTests(unittest.TestCase):
    def test_complete_finding_passes_through(self) -> None:
        finding, warnings = validate_finding({
            "claim": "量子计算短期内不会打破 RSA",
            "source_url": "https://example.com/paper",
            "confidence": "已知",
            "lens": "academic",
        })
        self.assertEqual(warnings, [])
        self.assertEqual(finding["confidence"], "已知")
        self.assertEqual(finding["source_url"], "https://example.com/paper")

    def test_missing_source_url_downgrades_to_guess(self) -> None:
        finding, warnings = validate_finding({
            "claim": "没有来源的判断",
            "confidence": "已知",
        })
        self.assertEqual(finding["confidence"], CONFIDENCE_GUESS)
        self.assertTrue(any("source_url" in w for w in warnings))

    def test_invalid_confidence_downgrades_to_guess(self) -> None:
        finding, warnings = validate_finding({
            "claim": "某判断",
            "source_url": "https://example.com/x",
            "confidence": "确定",
        })
        self.assertEqual(finding["confidence"], CONFIDENCE_GUESS)
        self.assertTrue(any("confidence" in w for w in warnings))

    def test_empty_claim_warns(self) -> None:
        finding, warnings = validate_finding({
            "claim": "   ",
            "source_url": "https://example.com/x",
            "confidence": "已知",
        })
        self.assertTrue(any("claim" in w for w in warnings))

    def test_confidence_levels_are_exactly_known_inferred_guess(self) -> None:
        self.assertEqual(CONFIDENCE_LEVELS, ("已知", "推断", "猜测"))


class HandlerFindingSchemaTests(unittest.TestCase):
    def test_claim_findings_are_validated_on_append(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler("Q", MemoryStore(directory), object())
            handler._append_finding({
                "claim": "无来源 claim 应被降级",
                "confidence": "已知",
                "lens": "skeptic",
            })
            self.assertEqual(len(handler.findings), 1)
            stored = handler.findings[0]
            self.assertEqual(stored["confidence"], CONFIDENCE_GUESS)
            self.assertTrue(handler._finding_warnings)

    def test_raw_material_records_pass_through_unvalidated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler("Q", MemoryStore(directory), object())
            handler._append_finding({"type": "exploration", "data": {"results": []}})
            self.assertEqual(len(handler.findings), 1)
            self.assertEqual(handler.findings[0]["type"], "exploration")
            self.assertFalse(handler._finding_warnings)

    def test_sub_research_triples_are_ingested_as_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler("Q", MemoryStore(directory), object())
            handler._append_finding({
                "claim": "A",
                "source_url": "http://a.example",
                "confidence": "已知",
                "lens": "skeptic",
            })
            handler._append_finding({
                "claim": "B",
                "source_url": "",
                "confidence": "已知",  # will be downgraded
                "lens": "economist",
            })
            stored = handler.findings[1]
            self.assertEqual(stored["confidence"], CONFIDENCE_GUESS)

    def test_known_requires_source_audit_invariant(self) -> None:
        """After P5 ingestion, no [已知] finding can lack a source."""
        with tempfile.TemporaryDirectory() as directory:
            handler = ResearchHandler("Q", MemoryStore(directory), object())
            handler._append_finding({"claim": "x", "confidence": "已知"})
            self.assertEqual(handler.findings[0]["confidence"], CONFIDENCE_GUESS)
            for finding in handler.findings:
                if finding.get("confidence") == CONFIDENCE_KNOWN:
                    self.assertTrue(finding.get("source_url"))


if __name__ == "__main__":
    unittest.main()
