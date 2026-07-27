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

from .handler import ResearchHandler  # pyright: ignore[reportMissingImports]
from .memory import MemoryStore
from .prompts import SYSTEM_PROMPT_TEMPLATE  # pyright: ignore[reportMissingImports]
from .tools import TOOLS_SCHEMA  # pyright: ignore[reportMissingImports]


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


def format_memories(memories: Sequence[dict[str, Any]]) -> str:
    """Render retrieved memory records into concise system-prompt context."""
    if not memories:
        return "No relevant prior memories found."

    entries: list[str] = []
    for memory in memories:
        layer = memory.get("layer", "memory")
        content = memory.get("content", memory.get("insight", str(memory)))
        entries.append(f"[{layer}] {content}")
    return "\n".join(entries)


async def research_loop(
    llm_client: Any,
    question: str,
    max_turns: int = 25,
) -> str:
    """Run the full -1 → 4 research pipeline and return its final brief.

    Step 0 (conversational): refine the user's raw question into a
    well-scoped research question before entering the STORM pipeline.
    """
    memory = MemoryStore("memory/")

    # ── Step 0: conversational layer — refine the research question ──
    refine_prompt = REFINE_QUESTION_PROMPT.format(question=question)
    refine_response = await llm_client.chat(
        messages=[{"role": "user", "content": refine_prompt}],
        role="conversational",
    )
    refined_question = (refine_response.content or question).strip()
    if not refined_question:
        refined_question = question

    # ── Research pipeline ──
    handler = ResearchHandler(question, memory, llm_client)
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

    for turn in range(1, max_turns + 1):
        stage_prompt = await handler.get_stage_prompt()
        if stage_prompt:
            messages.append({"role": "user", "content": stage_prompt})

        response = await llm_client.chat(messages=messages, tools=TOOLS_SCHEMA, role="tool_calling")
        if not response.tool_calls:
            if handler.stage >= 4:
                final_response = await llm_client.chat(messages=messages, tools=[], role="conversational")
                return final_response.content
            continue

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
            messages.append({"role": "user", "content": FINAL_REPORT_PROMPT})
            final_response = await llm_client.chat(messages=messages, tools=[], role="conversational")
            return final_response.content

    return "Research reached the maximum turn limit."
