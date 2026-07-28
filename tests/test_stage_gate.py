import asyncio
import tempfile
import unittest

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

            prompt = asyncio.run(handler.get_stage_prompt())

        self.assertEqual(handler.stage, 4)
        self.assertIsNotNone(prompt)
        assert isinstance(prompt, str)
        self.assertIn("同行评审", prompt)
        self.assertIn("finding_1", prompt)
        self.assertEqual(
            handler.adversarial_results["finding_1"]["status"],
            "needs_revision",
        )


if __name__ == "__main__":
    unittest.main()
