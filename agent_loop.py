"""Async execution loop for a staged research session."""

from __future__ import annotations

import json
from typing import Any, Sequence

from .handler import ResearchHandler  # pyright: ignore[reportMissingImports]
from .memory import MemoryStore
from .prompts import SYSTEM_PROMPT_TEMPLATE  # pyright: ignore[reportMissingImports]
from .tools import TOOLS_SCHEMA  # pyright: ignore[reportMissingImports]


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
    """Run the full -1 → 4 research pipeline and return its final brief."""
    memory = MemoryStore("memory/")
    handler = ResearchHandler(question, memory, llm_client)
    relevant_memories = memory.search(
        question,
        layers=["L2_domain", "L3_thinking_sops"],
    )
    memory_context = format_memories(relevant_memories)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        question=question,
        memory_context=memory_context,
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
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
