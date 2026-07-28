"""Async execution loop for a staged research session.

Role-to-model routing (configured via ``LLM_*`` env vars):

    conversational  — user interaction: question refinement + final report
    tool_calling    — main loop: tool selection and pipeline orchestration
    creative        — divergent thinking: lens discovery + perspective reflection
    content_review  — adversarial gate: challenge, confidence scoring
"""

from __future__ import annotations

import json
from typing import Any, Sequence

try:
    from .handler import ResearchHandler  # pyright: ignore[reportMissingImports]
    from .memory import MemoryStore
    from .prompts import SYSTEM_PROMPT_TEMPLATE  # pyright: ignore[reportMissingImports]
    from .tools import TOOLS_SCHEMA  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - direct script execution path.
    from handler import ResearchHandler  # pyright: ignore[reportMissingImports]
    from memory import MemoryStore
    from prompts import SYSTEM_PROMPT_TEMPLATE  # pyright: ignore[reportMissingImports]
    from tools import TOOLS_SCHEMA  # pyright: ignore[reportMissingImports]


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

FINAL_REPORT_PROMPT = (
    "基于以上四阶段研究，生成最终的完整研究简报。包含: 摘要、关键发现（标注置信度）、"
    "隐藏连接、可操作建议、前沿问题和已知局限。"
)

MAX_CONSECUTIVE_NO_TOOL_RESPONSES = 3


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


async def research_loop(
    llm_client: Any,
    question: str,
    max_turns: int = 100,
    on_status: Any = None,
    on_stage: Any = None,
    handler: Any = None,
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
        handler = ResearchHandler(question, memory, llm_client, on_status=on_status, on_stage=on_stage)
    else:
        handler.question = question
        handler.memory = memory
        handler.llm = llm_client
        handler.on_status = on_status
        handler.on_stage = on_stage
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

    consecutive_no_tool_responses = 0

    for turn in range(1, max_turns + 1):
        stage_prompt = await handler.get_stage_prompt()
        if stage_prompt:
            messages.append({"role": "user", "content": stage_prompt})

        _status("Requesting the next research action…")
        response = await llm_client.chat(messages=messages, tools=TOOLS_SCHEMA, role="tool_calling")

        if response.error:
            raise RuntimeError(f"Research model request failed: {response.error}")

        # Final report trigger: stage >= 4 and agent has stopped calling tools (or we force it)
        reached_end = handler.stage >= 4 and handler.findings
        if not response.tool_calls and reached_end:
            _status("Composing final report…")
            if response.content:
                messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": FINAL_REPORT_PROMPT})
            final_response = await llm_client.chat(messages=messages, tools=[], role="conversational")
            return final_response.content

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
                "content": "Continue the research pipeline by calling the next required tool.",
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

        if handler.stage >= 4 and handler.findings and turn > 5:
            _status("Generating final research brief…")
            messages.append({"role": "user", "content": FINAL_REPORT_PROMPT})
            final_response = await llm_client.chat(messages=messages, tools=[], role="conversational")
            return final_response.content

    return "Research reached the maximum turn limit."
