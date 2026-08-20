"""Stage controller and async tool dispatcher for the research pipeline."""

from __future__ import annotations

from dataclasses import dataclass
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
    )
    from .tools import (  # pyright: ignore[reportMissingImports]
        audit_document,
        do_challenge,
        do_crystallize,
        do_explore,
        do_reflect,
        do_sub_research,
        fetch_and_extract,
        validate_finding,
        web_search,
    )
except ImportError:  # pragma: no cover - direct script execution path.
    from lenses import discover_lenses  # pyright: ignore[reportMissingImports]
    from memory import MemoryStore
    from prompts import (  # pyright: ignore[reportMissingImports]
        STAGE1_MULTI_PERSPECTIVE,
        STAGE2_CONTRADICTION_MAP,
        STAGE3_SYNTHESIS,
        STAGE35_ADVERSARIAL_GATE,
    )
    from tools import (  # pyright: ignore[reportMissingImports]
        audit_document,
        do_challenge,
        do_crystallize,
        do_explore,
        do_reflect,
        do_sub_research,
        fetch_and_extract,
        validate_finding,
        web_search,
    )


@dataclass
class StepOutcome:
    """Result returned after a research tool has been executed."""

    data: Any
    next_prompt: Optional[str] = None
    should_exit: bool = False


class ResearchHandler:
    """Route tools and advance the distinct stages of the STORM pipeline."""

    def __init__(self, question: str, memory: MemoryStore, llm_client: Any, on_status: Any = None, on_stage: Any = None, report_language: str | None = None) -> None:
        self.question = question
        self.memory = memory
        self.llm = llm_client
        self.on_status = on_status
        self.on_stage = on_stage
        self.report_language = report_language
        self.stage: int | float = -1
        self.findings: list[dict[str, Any]] = []
        self.lenses_used: set[str] = set()
        self.dynamic_lenses: list[dict[str, Any]] = []
        self.adversarial_results: dict[str, dict[str, Any]] = {}
        self.confidence_scores: dict[str, Any] = {}
        # P6/P2: stage artifacts captured at stage boundaries (contradiction
        # map, synthesis, gate results) — consumed by document_audit and
        # persisted to disk before any context truncation.
        self.stage_artifacts: dict[str, str] = {}
        # P2/P8: document-level audit outcome and the gate credential that
        # permits advancing to the final brief (audit pass OR explicit downgrade).
        self.audit_result: dict[str, Any] | None = None
        self.gate_credential: dict[str, Any] | None = None
        self.open_questions: list[str] = []
        # The source fetcher is injectable for deterministic tests; production
        # audits use the same bounded HTTP(S) extractor as ``explore``.
        self.source_fetcher: Any = fetch_and_extract
        # P5: schema violations recorded during finding ingestion.
        self._finding_warnings: list[str] = []
        self._finding_counter = 0
        self.should_exit = False

    def _append_finding(self, finding: dict[str, Any]) -> None:
        """Append a finding, enforcing the P5 schema on claim-carrying entries.

        Raw material records (exploration/reflection dumps without a ``claim``)
        pass through untouched; claim-level findings are validated and
        downgraded to 猜测 when they lack a locatable source.
        """
        if "claim" in finding:
            normalized, warnings = validate_finding(finding)
            self._finding_counter += 1
            normalized.setdefault("finding_id", f"finding_{self._finding_counter}")
            self._finding_warnings.extend(warnings)
            if warnings and self.on_status:
                self.on_status(f"Finding schema: {warnings[0]}")
            self.findings.append(normalized)
        else:
            self.findings.append(finding)

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
        self._append_finding({"type": "exploration", "data": result})
        return StepOutcome(result)

    async def do_reflect(self, args: dict[str, Any], response: Any) -> StepOutcome:
        lens = str(args["lens"])
        if self.on_status:
            self.on_status(f"Analyzing with {lens} lens…")
        self.lenses_used.add(lens)
        result = await do_reflect(args, self.llm)
        self._append_finding({"type": "reflection", "lens": lens, "data": result})
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
            self.adversarial_results[target] = {
                "status": status,
                "data": result,
                # Decorrelation provenance: whether this challenge ran on a
                # logical skeleton (context-level decontamination) and whether
                # it was grounded in retrieved sources (capability-level
                # ceiling acknowledged). Not-grounded "challenged" verdicts are
                # model judgment, not independent confirmation.
                "skeletonized": bool(args.get("skeleton", False)),
                "grounded": bool(args.get("grounding", False)),
            }
        return StepOutcome(result)

    async def do_crystallize(self, args: dict[str, Any], response: Any) -> StepOutcome:
        if self.on_status:
            self.on_status(f"Crystallizing: {str(args.get('category', ''))}…")
        result = await do_crystallize(args, self.memory)
        if self.on_status:
            self.on_status("Crystallization saved; continuing research…")
        return StepOutcome(result)

    async def do_document_audit(self, args: dict[str, Any], response: Any) -> StepOutcome:
        """Document-level audit against the six-item rubric (P2).

        Running the audit records the gate credential (P8): a pass grants
        ``audit_pass``; an explicit ``downgrade_note`` on a failing audit
        grants ``downgrade`` with the reason appended to ``open_questions``.
        Without either, the state machine refuses to advance to the final brief.
        """
        if self.on_status:
            self.on_status("Document audit: running 6-point rubric…")
        result = await audit_document(
            self.findings,
            self.lenses_used,
            self.dynamic_lenses,
            self.stage_artifacts,
            self.llm,
            on_status=self.on_status,
            source_fetcher=self.source_fetcher,
        )
        self.audit_result = result

        downgrade_note = str(args.get("downgrade_note", "")).strip()
        if downgrade_note:
            self.open_questions.append(f"[降级] {downgrade_note}")
            self.gate_credential = {"type": "downgrade", "reason": downgrade_note}
            result["downgrade_recorded"] = True
        elif result.get("passed"):
            self.gate_credential = {"type": "audit_pass", "detail": "document_audit passed"}

        if self.on_status:
            status = "PASS" if result.get("passed") else "FAIL"
            self.on_status(
                f"Document audit: {status} ({len(result.get('gaps', []))} gaps)"
                + ("，已记录显式降级" if downgrade_note else "")
            )
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

        result = await do_sub_research(tasks, self.llm, self.memory, on_status=self.on_status, report_language=self.report_language)

        # Register every lens so the Stage 1 gate (handler.py:166) advances,
        # and ingest the distilled (claim, source_url, confidence) triples as
        # schema-enforced findings for the document audit.
        for task in tasks:
            lens = str(task.get("lens", ""))
            if lens:
                self.lenses_used.add(lens)
        for task_result in result.get("task_results", []):
            lens = str(task_result.get("lens", ""))
            for triple in task_result.get("results", []):
                if isinstance(triple, dict) and triple.get("claim"):
                    self._append_finding({
                        "claim": triple.get("claim"),
                        "source_url": triple.get("source_url", ""),
                        "confidence": triple.get("confidence", ""),
                        "lens": lens or triple.get("lens", ""),
                    })

        self._append_finding({"type": "sub_research", "data": result})
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
            # The gate requires (a) at least one real challenge, and (b) a
            # P8 gate credential: document_audit pass OR an explicit downgrade
            # record. Without both, the pipeline keeps waiting. Findings that
            # need revision remain attached to the session context; the final
            # report generator can review them from the conversation history
            # without a separate peer-review stage.
            if len(self.adversarial_results) == 0:
                return None  # agent hasn't called challenge yet — keep waiting
            if self.audit_result is None:
                return None  # document audit not run — no gate credential yet
            if self.audit_result.get("passed"):
                self.gate_credential = {"type": "audit_pass", "detail": "document_audit passed"}
            if self.gate_credential is None:
                return None  # audit failed and no explicit downgrade — keep waiting
            self.stage = 4
            if self.on_status:
                self.on_status("Adversarial gate complete — generating final brief…")
            if self.on_stage:
                self.on_stage(4, "生成最终简报")

        return None
