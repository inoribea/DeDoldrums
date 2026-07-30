"""Stage controller and async tool dispatcher for the research pipeline."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Optional
import uuid

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
    from .tools import do_challenge, do_crystallize, do_explore, do_reflect, do_sub_research, web_search  # pyright: ignore[reportMissingImports]
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
    from tools import do_challenge, do_crystallize, do_explore, do_reflect, do_sub_research, web_search  # pyright: ignore[reportMissingImports]


@dataclass
class StepOutcome:
    """Result returned after a research tool has been executed."""

    data: Any
    next_prompt: Optional[str] = None
    should_exit: bool = False


class ResearchHandler:
    """Route tools and advance the distinct stages of the STORM pipeline."""

    def __init__(self, question: str, memory: MemoryStore, llm_client: Any, on_status: Any = None, on_stage: Any = None) -> None:
        self.question = question
        self.memory = memory
        self.llm = llm_client
        self.on_status = on_status
        self.on_stage = on_stage
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
        source = args.get("source", "web")
        query = str(args.get("query", ""))[:80]
        if self.on_status:
            if source == "web":
                self.on_status(f"Searching web: {query}…")
            elif source == "url":
                self.on_status(f"Reading: {args.get('url', '')[:60]}…")
            elif source == "memory":
                self.on_status(f"Searching memory: {query}…")
        result = await do_explore(args, self.memory)
        self.findings.append({"type": "exploration", "data": result})
        return StepOutcome(result)

    async def do_reflect(self, args: dict[str, Any], response: Any) -> StepOutcome:
        lens = str(args["lens"])
        if self.on_status:
            self.on_status(f"Analyzing with {lens} lens…")
        self.lenses_used.add(lens)
        result = await do_reflect(args, self.llm)
        self.findings.append({"type": "reflection", "lens": lens, "data": result})
        return StepOutcome(result)

    async def do_challenge(self, args: dict[str, Any], response: Any) -> StepOutcome:
        if self.on_status:
            self.on_status(f"Challenge: {args.get('mode', 'all')}")
        result = await do_challenge(args, self.llm, on_status=self.on_status)
        if self.stage == 3.5:
            target = str(args.get("target", ""))[:120]
            if not target:
                target = f"finding_{uuid.uuid4().hex[:8]}"
            # Language-independent verdict: structured dicts, not substring matching
            challenges = result.get("challenges", {})
            has_issues = False
            has_inconclusive = False
            for verdict in challenges.values():
                if isinstance(verdict, dict):
                    v = verdict.get("verdict", "")
                    if v == "issues_found":
                        has_issues = True
                    elif v == "inconclusive":
                        has_inconclusive = True
                else:
                    # Legacy fallback: raw string response (shouldn't happen post-migration)
                    has_inconclusive = True

            if has_issues:
                status = "needs_revision"
            elif has_inconclusive:
                status = "inconclusive"
            else:
                status = "challenged"
            self.adversarial_results[target] = {"status": status, "data": result}
        return StepOutcome(result)

    async def do_crystallize(self, args: dict[str, Any], response: Any) -> StepOutcome:
        if self.on_status:
            self.on_status(f"Crystallizing: {str(args.get('category', ''))}…")
        result = await do_crystallize(args, self.memory)
        if self.on_status:
            self.on_status("Crystallization saved; continuing research…")
        return StepOutcome(result)

    async def do_sub_research(self, args: dict[str, Any], response: Any) -> StepOutcome:
        """Fan-out parallel sub-agents: one ``sub_research`` call with multiple lens tasks.

        Delegates to the module-level ``do_sub_research`` which pre-fetches
        web search per task and runs concurrent single-turn LLM analysis.
        Lens registration ensures the Stage 1 gate (``lenses_used >= 3``)
        advances correctly when this tool replaces sequential ``reflect`` calls.
        """
        tasks = args.get("tasks", [])
        if not tasks:
            return StepOutcome({"error": "tasks is required"})

        if self.on_status:
            lens_labels = ", ".join(str(t.get("lens", "")) for t in tasks[:3])
            self.on_status(f"Parallel sub-research: {len(tasks)} lenses ({lens_labels})…")

        result = await do_sub_research(tasks, self.llm, self.memory, on_status=self.on_status)

        # Register every lens so the Stage 1 gate (handler.py:166) advances.
        for task in tasks:
            lens = str(task.get("lens", ""))
            if lens:
                self.lenses_used.add(lens)

        self.findings.append({"type": "sub_research", "data": result})
        return StepOutcome(result)

    async def get_stage_prompt(self) -> Optional[str]:
        """Return the next stage instruction, advancing only at its defined gate."""
        if self.stage == -1:
            if self.on_status:
                self.on_status("Stage 0: Discovering perspectives…")
            if self.on_stage:
                self.on_stage(0, "动态视角发现")
            # Search web for context before lens discovery
            search_results: list[dict[str, str]] = []
            try:
                search_results = await web_search(self.question, max_results=5)
            except Exception:
                pass  # if search fails, proceed without context
            self.dynamic_lenses = await discover_lenses(self.question, self.llm, search_results)
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
                if self.on_status:
                    self.on_status("Stage 1: Multi-perspective scan…")
                if self.on_stage:
                    self.on_stage(1, "多视角扫描")
                return STAGE1_MULTI_PERSPECTIVE.format(
                    question=self.question,
                    lenses=self.dynamic_lenses,
                )
            return None

        if self.stage == 1:
            if len(self.lenses_used) >= 3:
                self.stage = 2
                if self.on_status:
                    self.on_status("Stage 2: Mapping contradictions…")
                if self.on_stage:
                    self.on_stage(2, "矛盾映射")
                return STAGE2_CONTRADICTION_MAP
            return None

        if self.stage == 2:
            self.stage = 3
            if self.on_status:
                self.on_status("Stage 3: Synthesizing findings…")
            if self.on_stage:
                self.on_stage(3, "综合合成")
            return STAGE3_SYNTHESIS

        if self.stage == 3:
            self.stage = 3.5
            if self.on_status:
                self.on_status("Stage 3.5: Adversarial verification gate…")
            if self.on_stage:
                self.on_stage(3.5, "对抗验证闸门")
            return STAGE35_ADVERSARIAL_GATE

        if self.stage == 3.5:
            # The gate requires at least one real challenge. Findings that need revision
            # remain attached to the session for peer review instead of blocking the
            # pipeline forever: there is no separate tool that can transition them back.
            if len(self.adversarial_results) == 0:
                return None  # agent hasn't called challenge yet — keep waiting
            self.stage = 4
            if self.on_status:
                self.on_status("Stage 4: Peer review…")
            if self.on_stage:
                self.on_stage(4, "同行评审")
            unresolved = {
                target: value
                for target, value in self.adversarial_results.items()
                if value.get("status") == "needs_revision"
            }
            if not unresolved:
                return STAGE4_PEER_REVIEW
            review_context = json.dumps(unresolved, ensure_ascii=False)[:4000]
            return (
                f"{STAGE4_PEER_REVIEW}\n\n"
                "以下对抗验证发现仍待修订。必须在同行评审中逐项处理：\n"
                f"{review_context}"
            )

        return None
