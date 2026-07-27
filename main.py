"""Command-line entry point for a ResearchAgent session."""

import argparse
import asyncio
from typing import Any

try:  # Support both ``python main.py`` and ``python -m research_agent.main``.
    from .agent_loop import research_loop  # pyright: ignore[reportMissingImports]
    from .config import get_config
    from .goal_mode import ResearchGoalMode  # pyright: ignore[reportMissingImports]
    from .llm import LLMClient
    from .memory import MemoryStore
except ImportError:  # pragma: no cover - exercised by direct script execution.
    from agent_loop import research_loop  # pyright: ignore[reportMissingImports]
    from config import get_config
    from goal_mode import ResearchGoalMode  # pyright: ignore[reportMissingImports]
    from llm import LLMClient
    from memory import MemoryStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a multi-perspective research session.")
    parser.add_argument("question", help="Research question to investigate")
    parser.add_argument("--goal", action="store_true", help="Continue researching until the budget ends")
    parser.add_argument("--budget", type=int, default=30, metavar="MINUTES", help="Goal-mode budget (default: 30)")
    parser.add_argument("--max-turns", type=int, default=50, help="Maximum LLM turns (default: 50)")
    args = parser.parse_args()
    if args.budget <= 0 or args.max_turns <= 0:
        parser.error("--budget and --max-turns must be positive")
    return args


async def _run_goal_mode(client: Any, question: str, budget: int, max_turns: int) -> str:
    goal = ResearchGoalMode(question, budget_minutes=budget, max_turns=max_turns)
    brief = ""
    while True:
        continuation = goal.check()
        if continuation == "/exit":
            return brief or "研究在生成简报前结束。"
        brief = await research_loop(client, f"{question}\n\n{continuation}", max_turns=max_turns)
        goal.save_state()
        if goal.state["status"] == "wrapping_up":
            return brief


async def main() -> None:
    """Parse CLI arguments, run the selected mode, then archive the result."""
    args = parse_args()
    config = get_config()
    client = LLMClient(api_key=config["api_key"], base_url=config["base_url"], model=config["model"])
    if args.goal:
        brief = await _run_goal_mode(client, args.question, args.budget, args.max_turns)
    else:
        brief = await research_loop(client, args.question, args.max_turns)

    print(brief)
    memory = MemoryStore("memory/")
    await asyncio.to_thread(memory.archive_session, args.question, [{"final_brief": brief}])


if __name__ == "__main__":
    asyncio.run(main())
