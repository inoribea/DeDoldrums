"""Dynamic research-lens discovery with a proven fallback library."""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping, Protocol, Sequence


LOGGER = logging.getLogger(__name__)


LENS_LIBRARY: dict[str, dict[str, Any]] = {
    "practitioner": {
        "name": "实践者",
        "identity": "你是一个每天与这个话题打交道的从业者。你看到的是教科书不会写的真实情况。",
        "concerns": "实际可用性、隐性成本、常见坑、非正式的最佳实践",
        "blind_spot": "容易忽视理论突破和长期趋势",
        "temperature": 0.8,
    },
    "skeptic": {
        "name": "怀疑论者",
        "identity": "你相信主流观点是错的（或至少被严重夸大）。你的工作是找到最有力的反证。",
        "concerns": "夸大宣传、幸存者偏差、被压制的负面证据、利益冲突",
        "blind_spot": "可能忽视真实的进步和共识形成的原因",
        "temperature": 0.9,
    },
    "economist": {
        "name": "经济学家",
        "identity": "你跟的是钱。每一个叙事背后都有不被明说的经济激励。",
        "concerns": "谁出钱、谁赚钱、激励结构、市场集中度、沉没成本",
        "blind_spot": "容易忽视非经济价值（文化、伦理、美感）",
        "temperature": 0.7,
    },
    "historian": {
        "name": "历史学家",
        "identity": "你见过这个模式。历史上总有类似的事情发生过——关键是从上次的结局中学到什么。",
        "concerns": "历史类比、模式重复、上次怎么失败的、制度惯性",
        "blind_spot": "可能过度依赖类比而忽视质变（真正的范式转移）",
        "temperature": 0.8,
    },
    "academic": {
        "name": "学者",
        "identity": "你读过原始文献——不是媒体报道、不是推文、不是综述文章。你知道研究实际说了什么。",
        "concerns": "效应量、方法严谨性、可复现性、发表偏倚",
        "blind_spot": "可能忽视实践智慧和市场信号",
        "temperature": 0.5,
    },
    "first_principles": {
        "name": "第一性原理",
        "identity": "你拒绝类比。把问题拆到不可再分的物理/逻辑原子，从零重建理解。",
        "concerns": "基本约束、物理极限、逻辑必然性、信息边界",
        "blind_spot": "可能忽视社会/文化/制度层面的现实约束",
        "temperature": 0.6,
    },
    "counterfactual": {
        "name": "反事实推理",
        "identity": "你的工作是：假设关键条件发生了变化，重新推演整个逻辑链。",
        "concerns": "因果方向、必要条件 vs 充分条件、蝴蝶效应",
        "blind_spot": "可能产出有趣的思辨但缺乏实证锚点",
        "temperature": 0.9,
    },
    "newcomer": {
        "name": "新人",
        "identity": "你完全不了解这个领域。你会问出专家们忘记问的基础问题。",
        "concerns": "基础概念、常见误解、为什么重要、跟其他概念的关系",
        "blind_spot": "可能无法区分「专家共识」和「领域内争议」",
        "temperature": 0.7,
    },
    "systems_thinking": {
        "name": "系统思维",
        "identity": "你把研究对象看作一个相互关联的系统。你关注的是反馈回路、涌现性质和杠杆点。",
        "concerns": "反馈回路、延迟效应、非线性关系、边界条件、意外后果",
        "blind_spot": "可能过度抽象化，忽视个体能动性和具体案例",
        "temperature": 0.7,
    },
}


class ChatClient(Protocol):
    """Minimum async client interface required for dynamic lens discovery."""

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]] | None = None,
        temperature: float = 0.7,
        role: str | None = None,
    ) -> Any:
        """Return an object exposing a ``content`` attribute."""


def get_lens(key: str) -> dict[str, Any]:
    """Return the fallback configuration registered under ``key``."""
    return LENS_LIBRARY[key]


async def discover_lenses(
    question: str, llm_client: ChatClient, search_results: list[dict[str, str]] | None = None
) -> list[dict[str, Any]]:
    """Discover research-specific lenses, then add library lenses for coverage gaps.

    If *search_results* are provided, they are included as context so the LLM
    can derive perspectives from actual search snippets rather than guessing.
    """
    context_block = ""
    if search_results:
        snippets = "\n".join(
            f"- {r.get('title', '')}: {r.get('snippet', '')[:200]}"
            for r in search_results[:5]
        )
        context_block = f"\n\n相关材料概览:\n{snippets}"

    prompt = f"""研究问题: {question}{context_block}

识别研究这个问题需要的 3-5 个关键视角。每个视角必须覆盖不同的利益相关者或分析维度，
彼此互补而不重复，并且至少包含一个挑战主流观点的视角。

只返回 JSON 数组。数组中的每个对象必须严格包含:
{{
  "key": "视角标识符",
  "name": "中文名称",
  "identity": "一句话描述这个视角的身份和看问题的角度",
  "concerns": "这个视角最关心什么（逗号分隔）",
  "blind_spot": "这个视角容易忽略什么"
}}"""

    dynamic_lenses: list[dict[str, Any]] = []
    try:
        response = await llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            role="creative",
        )
        dynamic_lenses = _parse_dynamic_lenses(getattr(response, "content", ""))
        if getattr(response, "error", None):
            LOGGER.warning("Dynamic lens discovery failed: %s", response.error)
    except (OSError, TypeError, ValueError) as exc:
        LOGGER.warning("Dynamic lens discovery request failed: %s", exc)

    missing_types = _find_gaps(dynamic_lenses)
    fallback_lenses = [LENS_LIBRARY[key] for key in missing_types[:2]]
    return dynamic_lenses + fallback_lenses


def _find_gaps(dynamic_lenses: Sequence[Mapping[str, Any]]) -> list[str]:
    """Identify missing practitioner, skeptic, and academic coverage."""
    current_angles: set[str] = set()
    for lens in dynamic_lenses:
        identity = lens.get("identity", "")
        concerns = lens.get("concerns", "")
        text = f"{identity}{concerns}"
        if any(keyword in text for keyword in ["从业", "实践", "操作", "每天"]):
            current_angles.add("practitioner")
        if any(keyword in text for keyword in ["反对", "怀疑", "挑战", "批判", "反面"]):
            current_angles.add("skeptic")
        if any(keyword in text for keyword in ["学术", "研究", "文献", "论文"]):
            current_angles.add("academic")

    gaps: list[str] = []
    for required_lens in ("skeptic", "practitioner", "academic"):
        if required_lens not in current_angles:
            gaps.append(required_lens)
    return gaps


def _parse_dynamic_lenses(content: Any) -> list[dict[str, Any]]:
    """Parse and validate the JSON array requested from the language model."""
    if not isinstance(content, str) or not content.strip():
        return []

    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.endswith("```"):
            text = text[:-3].strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        LOGGER.warning("Dynamic lens discovery returned invalid JSON.")
        return []

    if isinstance(parsed, dict):
        parsed = parsed.get("lenses", [])
    if not isinstance(parsed, list):
        return []

    required_fields = ("key", "name", "identity", "concerns", "blind_spot")
    lenses: list[dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict) or not all(
            isinstance(item.get(field), str) and item[field].strip()
            for field in required_fields
        ):
            continue
        lenses.append({field: item[field].strip() for field in required_fields})
        if len(lenses) == 5:
            break
    return lenses
