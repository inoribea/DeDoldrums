"""Stage controller and async tool dispatcher for the research pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

try:
    from .lenses import discover_lenses  # pyright: ignore[reportMissingImports]
    from .memory import MemoryStore
    from .prompts import (  # pyright: ignore[reportMissingImports]
        STAGE1_MULTI_PERSPECTIVE,
        STAGE2_CONTRADICTION_MAP,
        STAGE3_SYNTHESIS,
        STAGE35_ADVERSARIAL_GATE,
        STAGE4_PEER_REVIEW,
    )
    from .tools import do_challenge, do_crystallize, do_explore, do_reflect  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - direct script execution path.
    from lenses import discover_lenses  # pyright: ignore[reportMissingImports]
    from memory import MemoryStore
    from prompts import (  # pyright: ignore[reportMissingImports]
        STAGE1_MULTI_PERSPECTIVE,
        STAGE2_CONTRADICTION_MAP,
        STAGE3_SYNTHESIS,
        STAGE35_ADVERSARIAL_GATE,
        STAGE4_PEER_REVIEW,
    )
    from tools import do_challenge, do_crystallize, do_explore, do_reflect  # pyright: ignore[reportMissingImports]


@dataclass
class StepOutcome:
    """Result returned after a research tool has been executed."""

    data: Any
    next_prompt: Optional[str] = None
    should_exit: bool = False


class ResearchHandler:
    """Route tools and advance the distinct stages of the STORM pipeline."""

    def __init__(self, question: str, memory: MemoryStore, llm_client: Any) -> None:
        self.question = question
        self.memory = memory
        self.llm = llm_client
        self.stage: int | float = -1
        self.findings: list[dict[str, Any]] = []
        self.lenses_used: set[str] = set()
        self.dynamic_lenses: list[dict[str, Any]] = []
        self.adversarial_results: dict[str, dict[str, Any]] = {}
        self.confidence_scores: dict[str, Any] = {}
        self.should_exit = False

    async def dispatch(
        self,
        tool_name: str,
        args: dict[str, Any],
        response: Any = None,
    ) -> StepOutcome:
        """Dispatch a tool call using the GenericAgent ``do_<tool>`` convention."""
        method = getattr(self, f"do_{tool_name}", None)
        if method is None:
            return StepOutcome(None, next_prompt=f"Unknown tool: {tool_name}")
        return await method(args, response)

    async def do_explore(self, args: dict[str, Any], response: Any) -> StepOutcome:
        result = await do_explore(args, response)
        self.findings.append({"type": "exploration", "data": result})
        return StepOutcome(result)

    async def do_reflect(self, args: dict[str, Any], response: Any) -> StepOutcome:
        lens = str(args["lens"])
        self.lenses_used.add(lens)
        result = await do_reflect(args, self.llm)
        self.findings.append({"type": "reflection", "lens": lens, "data": result})
        return StepOutcome(result)

    async def do_challenge(self, args: dict[str, Any], response: Any) -> StepOutcome:
        result = await do_challenge(args, self.llm)
        if self.stage == 3.5:
            target = str(args.get("target", len(self.adversarial_results)))
            status = result.get("status", args.get("status", "verified"))
            self.adversarial_results[target] = {"status": status, "data": result}
        return StepOutcome(result)

    async def do_crystallize(self, args: dict[str, Any], response: Any) -> StepOutcome:
        result = await do_crystallize(args, response)
        return StepOutcome(result)

    async def get_stage_prompt(self) -> Optional[str]:
        """Return the next stage instruction, advancing only at its defined gate."""
        if self.stage == -1:
            self.dynamic_lenses = await discover_lenses(self.question, self.llm)
            self.stage = 0
            return f"""[研究阶段 0/4: 动态视角发现]

研究问题: {self.question}

在开始多视角分析之前，先动态发现这个主题需要哪些视角。
使用 explore 工具检索相关材料，然后使用 reflect 工具
从检索结果中识别 3-5 个该主题独有的分析视角。

候选视角: {self.dynamic_lenses}

视角发现原则:
- 视角应覆盖不同的利益相关者或分析维度
- 至少包含 1 个挑战主流观点的视角
- 至少包含 1 个实践者（每天打交道的人）的视角
- 视角之间应相互补充，不重复
"""

        if self.stage == 0:
            if len(self.dynamic_lenses) >= 3:
                self.stage = 1
                return STAGE1_MULTI_PERSPECTIVE.format(
                    question=self.question,
                    lenses=self.dynamic_lenses,
                )
            return None

        if self.stage == 1:
            if len(self.lenses_used) >= 3:
                self.stage = 2
                return STAGE2_CONTRADICTION_MAP
            return None

        if self.stage == 2:
            self.stage = 3
            return STAGE3_SYNTHESIS

        if self.stage == 3:
            self.stage = 3.5
            return STAGE35_ADVERSARIAL_GATE

        if self.stage == 3.5:
            pending = [
                key
                for key, value in self.adversarial_results.items()
                if value.get("status") not in ("verified", "cannot_verify")
            ]
            if not pending:
                self.stage = 4
                return STAGE4_PEER_REVIEW
            return None

        return None
