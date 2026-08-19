"""P6: stage artifacts are persisted to disk BEFORE context truncation, and
can be recovered after an interrupt without re-running completed stages."""

import asyncio
import tempfile
import unittest

from agent_loop import (
    STAGE_ARTIFACT_BY_COMPLETED_STAGE,
    _persist_stage_artifact,
    _snapshot_recent_stage_output,
)
from memory import MemoryStore


class StageArtifactPersistenceTests(unittest.TestCase):
    def test_save_and_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = MemoryStore(directory)
            path = memory.save_stage_artifact("测试问题", "contradiction_map", "矛盾 A vs B")
            self.assertTrue(path.endswith("contradiction_map.md"))

            artifacts = memory.load_stage_artifacts("测试问题")
            self.assertEqual(artifacts.get("contradiction_map"), "矛盾 A vs B")

    def test_multiple_artifacts_are_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = MemoryStore(directory)
            memory.save_stage_artifact("Q", "contradiction_map", "map text")
            memory.save_stage_artifact("Q", "synthesis", "synth text")

            artifacts = memory.load_stage_artifacts("Q")
            self.assertEqual(artifacts["contradiction_map"], "map text")
            self.assertEqual(artifacts["synthesis"], "synth text")

    def test_load_missing_session_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = MemoryStore(directory)
            self.assertEqual(memory.load_stage_artifacts("不存在的会话"), {})

    def test_artifact_survives_archive_session(self) -> None:
        """Artifacts coexist with the session archive (same L4 session dir)."""
        with tempfile.TemporaryDirectory() as directory:
            memory = MemoryStore(directory)
            memory.save_stage_artifact("Q", "synthesis", "s1")
            memory.archive_session("Q", [{"final_brief": "b1"}])

            artifacts = memory.load_stage_artifacts("Q")
            self.assertIn("synthesis", artifacts)


class SnapshotTests(unittest.TestCase):
    def test_snapshot_takes_recent_assistant_prose(self) -> None:
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "q"},
            {"role": "assistant", "content": "老的输出"},
            {"role": "assistant", "content": "矛盾映射输出"},
        ]
        snapshot = _snapshot_recent_stage_output(messages)
        self.assertIn("矛盾映射输出", snapshot)
        self.assertNotIn("sys", snapshot)

    def test_stage_mapping_uses_completed_stage(self) -> None:
        self.assertEqual(STAGE_ARTIFACT_BY_COMPLETED_STAGE[2], "contradiction_map")
        self.assertEqual(STAGE_ARTIFACT_BY_COMPLETED_STAGE[3], "synthesis")
        self.assertEqual(STAGE_ARTIFACT_BY_COMPLETED_STAGE[3.5], "gate")

    def test_persist_stage_artifact_writes_disk_and_handler_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory = MemoryStore(directory)
            handler = type("H", (), {
                "stage_artifacts": {},
                "question": "Q",
                "memory": memory,
                "on_status": None,
            })()
            messages = [
                {"role": "assistant", "content": "矛盾映射输出内容"},
            ]

            asyncio.run(_persist_stage_artifact(handler, messages, 2))

            self.assertEqual(handler.stage_artifacts["contradiction_map"], "矛盾映射输出内容")
            recovered = memory.load_stage_artifacts("Q")
            self.assertEqual(recovered["contradiction_map"], "矛盾映射输出内容")


if __name__ == "__main__":
    unittest.main()
