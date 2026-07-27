"""Persistent budget-aware control for self-directed research."""

from __future__ import annotations

import json
import os
import time
from typing import Any


CONTINUATION_PROMPT = """[Goal Mode — 持续研究]

<research_question>
{question}
</research_question>

⏱ 已用 {elapsed_min:.0f} 分钟，剩余约 {remaining_min:.0f} 分钟。第 {turn} 次唤醒。

你在 Goal Mode 下持续深挖这个研究问题。无法宣告完成，会被不断唤醒直到预算耗尽。

每次唤醒后的流程（3选1）:
1. 探索阶段: 发现新的信息源、新的透镜角度、新的子问题
2. 检验阶段: 从不同视角严格审视当前结论
   - 换透镜（之前没用过的角度）
   - 设计更难的反例和测例
   - 检查引用源的时效性和权威性
   - 重新审视：是否遗漏了关键利益方或关键变量
   - 按研究主题轮换选用合适的透镜和方法
3. 深化阶段: 针对检验发现的问题，修正/补充/重新论证

原则:
1. 每次唤醒交替进行检验和深化，保留每次的检验报告和改进记录
2. 不要重写整个研究——在现有基础上修正和深化
3. 严格区分研究报告和进度日志
4. 若检验只发现无关紧要的问题 → 升级检验标准（更苛刻透镜/更难问题/对照原始问题重审）
5. 深化阶段禁止"无改动"——若检验未发现值得改的点，说明检验标准太低；输出标准升级报告
6. 在工作文件夹中记录进度
7. 所有阶段都建议使用 explore 检索新信息、使用 reflect 切换透镜
8. 当有值得固化的突破洞察时使用 crystallize
"""


BUDGET_LIMIT_PROMPT = """[Goal Mode — 预算耗尽，收口]

<research_question>
{question}
</research_question>

⏱ 预算已耗尽（{budget_min:.0f} 分钟）。这是最后一轮。

请执行收口:
1. 总结本次研究的所有关键发现（列表，标注置信度 1-10）
2. 列出未解决的子问题和建议的 next step
3. 标注最有价值的「前沿问题」（回答它会改变一切）
4. 使用 crystallize 固化值得保留的思维模式
5. 清理中间临时文件
"""


class ResearchGoalMode:
    """Track a time- and turn-bounded sequence of autonomous research passes."""

    def __init__(
        self,
        question: str,
        budget_minutes: int = 30,
        max_turns: int = 50,
    ) -> None:
        self.state: dict[str, Any] = {
            "question": question,
            "start_time": time.time(),
            "budget_seconds": budget_minutes * 60,
            "turns_used": 0,
            "max_turns": max_turns,
            "status": "running",
        }

    def save_state(self, path: str = "temp/research_goal_state.json") -> None:
        """Persist state so a later process can resume the current goal."""
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(self.state, file, ensure_ascii=False, indent=2)

    def check(self) -> str:
        """Return the next continuation instruction or the budget-limit instruction."""
        if self.state["status"] == "wrapping_up":
            self.state["status"] = "DONE"
            return "/exit"
        if self.state["status"] != "running":
            return "/exit"

        elapsed = time.time() - self.state["start_time"]
        remaining = self.state["budget_seconds"] - elapsed
        turn = self.state["turns_used"] + 1
        self.state["turns_used"] = turn

        if remaining <= 0 or turn > self.state["max_turns"]:
            self.state["status"] = "wrapping_up"
            return BUDGET_LIMIT_PROMPT.format(
                question=self.state["question"],
                budget_min=self.state["budget_seconds"] / 60,
            )

        return CONTINUATION_PROMPT.format(
            question=self.state["question"],
            elapsed_min=elapsed / 60,
            remaining_min=remaining / 60,
            turn=turn,
        )
