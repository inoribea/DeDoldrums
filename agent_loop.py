"""Async execution loop for a staged research session.

Role-to-model routing (configured via ``LLM_*`` env vars):

    conversational  — user interaction: question refinement + final report
    tool_calling    — main loop: tool selection and pipeline orchestration
    creative        — divergent thinking: lens discovery + perspective reflection
    content_review  — adversarial gate: challenge, confidence scoring
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

try:
    from .handler import ResearchHandler  # pyright: ignore[reportMissingImports]
    from .memory import MemoryStore
    from .prompts import SYSTEM_PROMPT_TEMPLATE  # pyright: ignore[reportMissingImports]
    from .tools import TOOLS_SCHEMA, _output_directive  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - direct script execution path.
    from handler import ResearchHandler  # pyright: ignore[reportMissingImports]
    from memory import MemoryStore
    from prompts import SYSTEM_PROMPT_TEMPLATE  # pyright: ignore[reportMissingImports]
    from tools import TOOLS_SCHEMA, _output_directive  # pyright: ignore[reportMissingImports]


REFINE_QUESTION_PROMPT = (
    "你是一个研究助手。用户提出了一个初始问题，请在开始多视角研究之前，"
    "将其精炼为更聚焦、更可研究的形式。\n\n"
    "要求:\n"
    "1. 如果原问题已经足够清晰，直接复述即可\n"
    "2. 如果原问题模糊或过于宽泛，将其收窄到可研究的范围\n"
    "3. 识别隐含的假设并明确化\n"
    "4. 只输出精炼后的问题，不要加任何前言或解释\n\n"
    "原始问题: {question}"
)

FINAL_REPORT_PROMPT_TEMPLATE = (
    "Based on the completed four-stage research, generate the final comprehensive "
    "research brief. Include: summary, key findings (with confidence scores), "
    "hidden connections, actionable recommendations, frontier questions, and "
    "known limitations.\n\n{output_directive}"
)

FINAL_REPORT_RETRY_PROMPT = (
    "Your prior final-report response was empty. Return the complete research brief now, "
    "with a non-empty summary, key findings, confidence, recommendations, and limitations."
)

MAX_CONSECUTIVE_NO_TOOL_RESPONSES = 3
FINAL_REPORT_ATTEMPTS = 3
FINAL_SYNTHESIS_TIMEOUT_SECONDS = 240.0
FINAL_REPORT_CONTEXT_MAX_CHARS = 24000
FINAL_REPORT_TRUNCATION_NOTICE = "\n\n[... truncated to keep final report input within budget ...]"


def _message_content_text(message: Mapping[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if content is None:
        return ""
    return str(content).strip()


def _message_size(message: Mapping[str, Any]) -> int:
    return len(json.dumps(dict(message), ensure_ascii=False))


def _fit_message_content(role: str, content: str, max_size: int) -> str | None:
    empty_size = _message_size({"role": role, "content": ""})
    if max_size < empty_size:
        return None

    if _message_size({"role": role, "content": content}) <= max_size:
        return content

    available = max_size - empty_size
    if available <= 0:
        return ""

    suffix = FINAL_REPORT_TRUNCATION_NOTICE
    if available <= len(suffix):
        fitted = suffix[-available:]
        while fitted and _message_size({"role": role, "content": fitted}) > max_size:
            fitted = fitted[1:]
        return fitted

    fitted = f"{content[:available - len(suffix)]}{suffix}"
    while fitted and _message_size({"role": role, "content": fitted}) > max_size:
        excess = _message_size({"role": role, "content": fitted}) - max_size
        keep = max(0, len(fitted) - len(suffix) - excess)
        fitted = f"{fitted[:keep]}{suffix}"
    return fitted


def _compact_final_report_messages(
    messages: Sequence[Mapping[str, Any]],
    max_chars: int = FINAL_REPORT_CONTEXT_MAX_CHARS,
) -> list[dict[str, Any]]:
    """Return bounded context for final report generation.

    Keep the input bounded to avoid context-overflow and excessive prefill cost.
    Long final reports are still protected separately by a longer read timeout.
    """
    if not messages:
        return []

    compact: list[dict[str, Any]] = []
    used_chars = 0

    for message in messages[:2]:
        role = str(message.get("role", "user"))
        content = _message_content_text(message)
        remaining = max_chars - used_chars
        fitted = _fit_message_content(role, content, remaining)
        if fitted is None:
            break
        compact_message = {"role": role, "content": fitted}
        compact.append(compact_message)
        used_chars += _message_size(compact_message)

    recent_assistant = [
        m for m in messages
        if m.get("role") == "assistant" and m.get("content")
    ]
    selected: list[dict[str, Any]] = []
    assistant_budget = max_chars - used_chars
    assistant_used = 0

    for message in reversed(recent_assistant):
        content = _message_content_text(message)
        remaining = assistant_budget - assistant_used
        fitted = _fit_message_content("assistant", content, remaining)
        if fitted is None:
            break
        compact_message = {"role": "assistant", "content": fitted}
        selected.append(compact_message)
        assistant_used += _message_size(compact_message)
        if assistant_used >= assistant_budget:
            break

    compact.extend(reversed(selected))
    return compact


def _sanitize_recovered_note(text: str) -> str:
    sanitized = text.strip()
    for marker in (
        "<｜｜DSML｜｜tool_calls>",
        "<||DSML||tool_calls>",
        "<tool_calls>",
    ):
        marker_index = sanitized.find(marker)
        if marker_index >= 0:
            sanitized = sanitized[:marker_index].rstrip()
    lines = [line for line in sanitized.splitlines() if "DSML" not in line]
    return "\n".join(lines).strip()


def _fallback_final_brief(compact_messages: Sequence[Mapping[str, Any]], reason: str) -> str:
    notes: list[str] = []
    for message in compact_messages:
        if message.get("role") != "assistant":
            continue
        note = _sanitize_recovered_note(_message_content_text(message))
        if note:
            notes.append(note)
    if not notes:
        raise RuntimeError(f"Final research brief failed: {reason}")

    excerpts = "\n\n".join(f"- {note}" for note in notes[-6:])
    return (
        "# Research brief (recovered)\n\n"
        "The final report generator failed after multiple attempts, so this recovered "
        "brief preserves the completed research and peer-review notes instead of "
        "discarding the session.\n\n"
        f"Failure reason: {reason}\n\n"
        "## Available research notes\n\n"
        f"{excerpts}\n\n"
        "## Known limitation\n\n"
        "This is a fallback brief assembled from completed pipeline outputs; it may be "
        "less polished than a freshly generated final synthesis."
    )


def format_memories(memories: Sequence[dict[str, Any]]) -> str:
    """Render retrieved memory records into concise system-prompt context."""
    if not memories:
        return "No relevant prior memories found."

    entries: list[str] = []
    for memory in memories:
        layer = memory.get("layer", "memory")
        # memory.search returns different shapes per layer:
        # L1 index: {"layer":"L1","type":"pattern_index","matches":[...]}
        # file-based: {"layer":"L2_domain","file":"...","snippet":"..."}
        if "snippet" in memory:
            entries.append(f"[{layer}] {memory['file']}: {memory['snippet'][:300]}")
        elif "matches" in memory:
            for m in memory["matches"][:3]:
                entries.append(f"[{layer}] {m.get('trigger','')}: {m.get('insight_summary','')[:200]}")
        else:
            entries.append(f"[{layer}] {str(memory)[:200]}")
    return "\n".join(entries)


def _lens_label(lens: Any) -> str:
    if isinstance(lens, Mapping):
        label = lens.get("key") or lens.get("name")
        return str(label) if label else ""
    return str(lens) if lens is not None else ""


def _no_tool_retry_prompt(handler: Any) -> str:
    stage = getattr(handler, "stage", None)
    if stage in (0, 1):
        dynamic_lenses = getattr(handler, "dynamic_lenses", [])
        lenses = dynamic_lenses if isinstance(dynamic_lenses, Sequence) else []
        used = getattr(handler, "lenses_used", set())
        used_lenses = {str(lens) for lens in used} if isinstance(used, set) else set()
        unused = [
            _lens_label(lens)
            for lens in lenses
            if _lens_label(lens) and _lens_label(lens) not in used_lenses
        ]
        remaining = max(0, 3 - len(used_lenses))
        lens_hint = f" Suggested unused lenses: {', '.join(unused[:3])}." if unused else ""
        return (
            "Stage 1 still needs tool calls: call the reflect tool with an unused "
            f"lens to reach at least 3 perspectives ({len(used_lenses)}/3 used, "
            f"{remaining} remaining).{lens_hint} Do not answer in plain text only."
        )

    if stage == 3.5 and not getattr(handler, "adversarial_results", {}):
        return (
            "Stage 3.5 adversarial gate is not complete: call the challenge tool "
            "on at least one key finding now. Plain-text critique does not count "
            "as passing the gate."
        )

    if stage in (2, 3):
        return (
            "Your analysis was recorded. To keep the pipeline moving, use a tool "
            "next: call reflect to formalize the analysis, challenge to test a "
            "key finding, or crystallize to save a durable insight."
        )

    return "Continue the research pipeline by calling the next required tool."


async def research_loop(
    llm_client: Any,
    question: str,
    max_turns: int = 100,
    on_status: Any = None,
    on_stage: Any = None,
    handler: Any = None,
    report_language: str | None = None,
) -> str:
    """Run the full -1 → 4 research pipeline and return its final brief.

    Step 0 (conversational): refine the user's raw question into a
    well-scoped research question before entering the STORM pipeline.

    If *on_status* is provided, it is called as ``on_status(message)``
    at each significant step. If *on_stage* is provided, it is called
    as ``on_stage(stage, description)`` on stage transitions.
    """
    def _status(msg: str) -> None:
        if on_status:
            on_status(msg)
    def _stage(stage: int | float, desc: str) -> None:
        if on_stage:
            on_stage(stage, desc)

    memory = MemoryStore("memory/")

    # ── Step 0: conversational layer — refine the research question ──
    _status("Refining research question…")
    refine_prompt = REFINE_QUESTION_PROMPT.format(question=question)
    refine_response = await llm_client.chat(
        messages=[{"role": "user", "content": refine_prompt}],
        role="conversational",
    )
    refined_question = (refine_response.content or question).strip()
    if not refined_question:
        refined_question = question

    # ── Research pipeline ──
    if handler is None:
        handler = ResearchHandler(question, memory, llm_client, on_status=on_status, on_stage=on_stage, report_language=report_language)
    else:
        handler.question = question
        handler.memory = memory
        handler.llm = llm_client
        handler.on_status = on_status
        handler.on_stage = on_stage
        handler.report_language = report_language
    _status("Starting multi-perspective research pipeline…")
    relevant_memories = memory.search(
        refined_question,
        layers=["L2_domain", "L3_thinking_sops"],
    )
    memory_context = format_memories(relevant_memories)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        question=refined_question,
        memory_context=memory_context,
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": refined_question},
    ]

    async def compose_final_brief() -> str:
        compact = _compact_final_report_messages(messages)

        total_chars = sum(_message_size(m) for m in compact)
        _status(
            f"Composing final brief ({len(compact)} messages, "
            f"~{total_chars // 4} estimated tokens)…"
        )

        output_directive = _output_directive(report_language)
        final_report_prompt = FINAL_REPORT_PROMPT_TEMPLATE.format(output_directive=output_directive)
        retry_messages = compact + [{"role": "user", "content": final_report_prompt}]
        last_failure = "empty response"
        for attempt in range(FINAL_REPORT_ATTEMPTS):
            response = await llm_client.chat(
                messages=retry_messages,
                tools=[],
                role="conversational",
                timeout=FINAL_SYNTHESIS_TIMEOUT_SECONDS,
            )
            if response.error:
                last_failure = response.error
                if attempt < FINAL_REPORT_ATTEMPTS - 1:
                    _status(f"Final brief attempt {attempt + 1} failed ({response.error}); retrying…")
                    continue
                _status(
                    "Final brief generator failed after retries; "
                    "returning recovered research notes…"
                )
                return _fallback_final_brief(compact, response.error)

            brief = response.content.strip()
            if brief:
                return brief

            last_failure = "empty final brief"
            if attempt < FINAL_REPORT_ATTEMPTS - 1:
                _status("Final research brief was empty; retrying…")
                retry_messages.append({"role": "user", "content": FINAL_REPORT_RETRY_PROMPT})
                continue

        _status("Final research brief was empty after retries; returning recovered research notes…")
        return _fallback_final_brief(compact, last_failure)

    consecutive_no_tool_responses = 0

    for turn in range(1, max_turns + 1):
        stage_prompt = await handler.get_stage_prompt()
        if stage_prompt:
            messages.append({"role": "user", "content": stage_prompt})

        if handler.stage >= 4:
            _status("Conducting final peer review…")
            peer_review = await llm_client.chat(
                messages=messages,
                tools=[],
                role="tool_calling",
                timeout=FINAL_SYNTHESIS_TIMEOUT_SECONDS,
            )
            if peer_review.error:
                raise RuntimeError(f"Final peer review failed: {peer_review.error}")
            if peer_review.tool_calls:
                raise RuntimeError("Final peer review returned unexpected tool calls.")
            peer_review_text = peer_review.content.strip()
            if not peer_review_text:
                raise RuntimeError("Final peer review was empty.")
            messages.append({"role": "assistant", "content": peer_review_text})
            _status("Generating final research brief…")
            return await compose_final_brief()

        _status("Requesting the next research action…")
        response = await llm_client.chat(messages=messages, tools=TOOLS_SCHEMA, role="tool_calling")

        if response.error:
            raise RuntimeError(f"Research model request failed: {response.error}")

        if not response.tool_calls:
            consecutive_no_tool_responses += 1
            if response.content:
                messages.append({"role": "assistant", "content": response.content})
            if consecutive_no_tool_responses >= MAX_CONSECUTIVE_NO_TOOL_RESPONSES:
                raise RuntimeError(
                    "Research model stopped issuing tool calls before the pipeline completed."
                )
            _status(
                "Research model returned no action; retrying "
                f"({consecutive_no_tool_responses}/{MAX_CONSECUTIVE_NO_TOOL_RESPONSES})…"
            )
            messages.append({
                "role": "user",
                "content": _no_tool_retry_prompt(handler),
            })
            continue

        consecutive_no_tool_responses = 0

        # Append assistant message with tool_calls before tool results
        # (required by OpenAI/DeepSeek API message ordering)
        messages.append({
            "role": "assistant",
            "content": response.content or None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in response.tool_calls
            ],
        })

        for tool_call in response.tool_calls:
            try:
                arguments = json.loads(tool_call.function.arguments)
            except (TypeError, json.JSONDecodeError):
                arguments = {}
            outcome = await handler.dispatch(
                tool_call.function.name,
                arguments,
                response,
            )
            if outcome.should_exit:
                return str(outcome.data)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(outcome.data, ensure_ascii=False),
                }
            )

    return "Research reached the maximum turn limit."
