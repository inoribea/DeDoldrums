"""Knowledge tools used by the ResearchAgent STORM pipeline."""

# pyright: reportMissingImports=false

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

try:
    from .lenses import LENS_LIBRARY, get_lens, get_lens
    from .memory import MemoryStore
    from .prompts import REFLECT_SYSTEM_PROMPT
except ImportError:  # Supports direct execution from the package directory.
    from lenses import LENS_LIBRARY, get_lens
    from memory import MemoryStore
    from prompts import REFLECT_SYSTEM_PROMPT


CHALLENGE_TIMEOUT_SECONDS = 45.0
SUB_RESEARCH_TIMEOUT_SECONDS = 60.0
MAX_SUB_RESULT_CHARS = 3000


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "explore",
            "description": "多层信息检索：搜索 web、查询记忆库、深度阅读指定 URL。用于收集研究问题所需的原始素材。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询词"},
                    "source": {
                        "type": "string",
                        "enum": ["web", "memory", "url"],
                        "description": "检索来源：web=搜索引擎, memory=本地记忆库, url=深度阅读指定网页",
                    },
                    "url": {"type": "string", "description": "当 source=url 时，指定要深度阅读的 URL"},
                    "max_results": {"type": "integer", "default": 5},
                },
                "required": ["query", "source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reflect",
            "description": "切换思维透镜审视当前发现。应用指定透镜（怀疑论/历史类比/经济分析/第一性原理/反事实推理等）对已有发现进行深度分析。用于突破单一视角的局限。",
            "parameters": {
                "type": "object",
                "properties": {
                    "lens": {
                        "type": "string",
                        "description": "思维透镜名称：skeptic, historian, economist, practitioner, academic, first_principles, counterfactual, systems_thinking, newcomer",
                    },
                    "focus": {"type": "string", "description": "应用透镜的具体焦点（哪条发现/哪个论点）"},
                    "findings_context": {"type": "string", "description": "当前已有的相关发现（摘要）"},
                },
                "required": ["lens", "focus"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "challenge",
            "description": "对抗性压力测试。对当前结论寻找逻辑漏洞、隐藏假设、缺失证据或替代解释。用于防止确认偏误和过早收敛。",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "要挑战的具体结论或论点"},
                    "context": {"type": "string", "description": "得出该结论的背景和依据"},
                    "mode": {
                        "type": "string",
                        "enum": ["logic_flaw", "hidden_assumption", "missing_evidence", "alternative_explanation", "all"],
                        "description": "挑战模式",
                    },
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crystallize",
            "description": "将突破性洞察或有效研究路径固化为可复用思维模式，写入记忆库。只在发现值得长期保留的模式时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "insight": {"type": "string", "description": "要固化的洞察或思维模式"},
                    "category": {
                        "type": "string",
                        "enum": ["domain_knowledge", "thinking_pattern", "lens_combination", "pitfall"],
                        "description": "固化类型",
                    },
                    "trigger_condition": {"type": "string", "description": "什么情况下应该召回这个模式（用于 L1 索引）"},
                },
                "required": ["insight", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sub_research",
            "description": "派发多个子代理并行研究不同视角。每个子代理独立搜索 web 并从一个透镜视角分析，所有结果并行执行后汇总返回。用于 Stage 1 多视角并行扫描——一次调用覆盖 2-3 个不同透镜，替代逐个串行 reflect。",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "maxItems": 3,
                        "description": "要并行执行的子研究任务列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "lens": {"type": "string", "description": "应用的思维透镜名称（如 skeptic, economist, historian 等）"},
                                "question": {"type": "string", "description": "该子代理的研究子问题"},
                            },
                            "required": ["lens", "question"],
                        },
                    },
                },
                "required": ["tasks"],
            },
        },
    },
]


async def do_explore(args: dict[str, Any], memory: MemoryStore) -> dict[str, Any]:
    """Retrieve research material from the web, memory, or a specific URL."""
    query = str(args.get("query", "")).strip()
    source = args.get("source", "web")
    max_results = max(1, min(int(args.get("max_results", 5)), 10))

    if not query:
        return {"source": source, "query": query, "results": [], "error": "query is required"}

    try:
        if source == "web":
            return {"source": "web", "query": query, "results": await web_search(query, max_results)}

        if source == "memory":
            results = memory.search(query, layers=["L2_domain", "L3_thinking_sops", "L4_archive"])
            return {"source": "memory", "query": query, "results": results}

        if source == "url":
            url = str(args.get("url", "")).strip()
            if not url:
                return {"source": "url", "query": query, "error": "url is required when source is url"}
            content = await fetch_and_extract(url)
            return {"source": "url", "url": url, "content": content[:5000], "length": len(content)}
    except (httpx.HTTPError, ValueError, OSError, RuntimeError) as exc:
        return {"source": source, "query": query, "results": [], "error": str(exc)}

    return {"source": source, "query": query, "results": [], "error": f"unsupported source: {source}"}


async def do_reflect(args: dict[str, Any], llm_client: Any) -> dict[str, str]:
    """Apply a named STORM thinking lens to the supplied findings."""
    lens = str(args.get("lens", "")).strip()
    focus = str(args.get("focus", "")).strip()
    lens_config = get_lens(lens)
    if lens_config is None:
        return {"lens": lens, "lens_name": "", "analysis": f"Unknown lens: {lens}"}
    if not focus:
        return {"lens": lens, "lens_name": lens_config["name"], "analysis": "focus is required"}

    prompt = REFLECT_SYSTEM_PROMPT.format(
        lens_name=lens_config["name"],
        identity=lens_config["identity"],
        concerns=lens_config["concerns"],
        blind_spot=lens_config["blind_spot"],
        focus=focus,
        findings_context=args.get("findings_context", ""),
    )
    analysis = await _call_llm(llm_client, prompt, lens_config["temperature"], role="creative")
    return {"lens": lens, "lens_name": lens_config["name"], "analysis": analysis}


async def do_challenge(args: dict[str, Any], llm_client: Any, on_status: Any = None) -> dict[str, Any]:
    """Stress-test a conclusion for logical and evidentiary weaknesses."""
    target = str(args.get("target", "")).strip()
    mode = args.get("mode", "all")
    context = str(args.get("context", ""))
    challenge_prompts = {
        "logic_flaw": "检查这个论点是否存在逻辑漏洞（循环论证、错误归因、非此即彼等）",
        "hidden_assumption": "找出这个论点依赖但未明说的隐藏假设",
        "missing_evidence": "指出需要但缺失的关键证据",
        "alternative_explanation": "提出能解释相同现象但结论不同的替代解释",
    }
    if not target:
        return {"target": target, "challenges": {}, "error": "target is required"}
    if mode not in (*challenge_prompts, "all"):
        return {"target": target, "challenges": {}, "error": f"unsupported mode: {mode}"}

    modes_to_run = challenge_prompts if mode == "all" else {mode: challenge_prompts[mode]}
    gathered = await asyncio.gather(*(
        _run_challenge_mode(current_mode, instruction, target, context, llm_client, on_status)
        for current_mode, instruction in modes_to_run.items()
    ), return_exceptions=True)
    results: dict[str, dict[str, str]] = {}
    for item in gathered:
        if isinstance(item, BaseException):
            results["unknown"] = {"mode": "unknown", "verdict": "inconclusive", "detail": f"{type(item).__name__}: {item}"}
        else:
            mode_name, verdict = item
            results[mode_name] = verdict
    return {"target": target, "challenges": results}


async def _run_challenge_mode(
    current_mode: str,
    instruction: str,
    target: str,
    context: str,
    llm_client: Any,
    on_status: Any = None,
) -> tuple[str, dict[str, str]]:
    if on_status:
        label = {
            "logic_flaw": "Logic check",
            "hidden_assumption": "Hidden assumptions",
            "missing_evidence": "Missing evidence",
            "alternative_explanation": "Alternative explanations",
        }.get(current_mode, current_mode)
        on_status(f"Challenge: {label}…")
    prompt = f"""As a rigorous peer reviewer, {instruction}.

Claim: {target}
Context: {context}

Be direct. If there are real issues, state them clearly. If the claim holds up, say so.

End your response with exactly one of these verdict lines:
VERDICT: ISSUES_FOUND
VERDICT: CLEAN"""
    try:
        result = await asyncio.wait_for(
            _call_llm(llm_client, prompt, 0.3, role="content_review"),
            timeout=CHALLENGE_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        return current_mode, {
            "mode": current_mode,
            "verdict": "inconclusive",
            "detail": f"Challenge timed out after {CHALLENGE_TIMEOUT_SECONDS:g}s.",
        }

    text = str(result).strip()
    if "VERDICT: ISSUES_FOUND" in text:
        verdict = "issues_found"
    elif "VERDICT: CLEAN" in text:
        verdict = "clean"
    else:
        # Model didn't follow the verdict format — treat as inconclusive
        verdict = "inconclusive"

    return current_mode, {"mode": current_mode, "verdict": verdict, "detail": text}


async def do_crystallize(args: dict[str, Any], memory: MemoryStore) -> dict[str, str]:
    """Persist a reusable insight in the appropriate memory layer."""
    insight = str(args.get("insight", "")).strip()
    category = str(args.get("category", "")).strip()
    trigger = str(args.get("trigger_condition", ""))
    if not insight or category not in {"domain_knowledge", "thinking_pattern", "lens_combination", "pitfall"}:
        return {"crystallized": "", "stored_in": "", "trigger": trigger, "error": "valid insight and category are required"}

    if category in {"thinking_pattern", "lens_combination"}:
        memory.save_sop(insight, trigger)
        memory.update_index(category, insight, trigger)
    elif category == "domain_knowledge":
        memory.save_domain_knowledge(insight)
    else:
        memory.save_pitfall(insight)

    return {"crystallized": category, "stored_in": memory.get_path(category), "trigger": trigger}


SUB_RESEARCH_PROMPT = """你是一个独立的研究子代理，从「{lens_name}」的视角分析以下问题。

## 研究问题
{question}

## 视角身份
{identity}

## 关注点
{concerns}

## 视角盲点（容易忽略的）
{blind_spot}

## 预检索结果
{pre_fetched}

要求：基于以上预检索结果和你的视角身份，产出结构化的分析。包含：
1. 关键发现（2-5 条，每条附带来源 URL）
2. 这个视角揭示了什么其他人会忽略的张力或洞察？
3. 需要进一步深挖的问题（1-3 个）

使用 Markdown 格式。使用中文。控制在 500 字以内。"""


async def do_sub_research(
    tasks: list[dict[str, Any]],
    llm_client: Any,
    memory: MemoryStore,
    on_status: Any = None,
) -> dict[str, Any]:
    """Fan-out parallel sub-agents: pre-fetch web search per task, then concurrent LLM analysis.

    Each sub-agent gets:
    - Its own web search results (pre-fetched via the module-level ``do_explore``)
    - A narrow briefing with lens identity, concerns, and blind spot
    - A single-turn LLM call — no tool-calling loops (v1 simplicity)

    All sub-agents run concurrently via ``asyncio.gather`` inside a single
    tool invocation — matching the ``do_challenge`` fan-out pattern.
    """
    if not tasks:
        return {"task_results": [], "error": "tasks is required"}

    # ── Phase 1: Pre-fetch web search for each task (fan-out) ──
    async def _pre_fetch(task: dict[str, Any]) -> dict[str, Any]:
        question = str(task.get("question", ""))
        lens = str(task.get("lens", ""))
        if on_status:
            on_status(f"[sub:{lens}] Searching web…")
        try:
            result = await do_explore({"query": question, "source": "web"}, memory)
        except Exception:
            result = {"results": []}
        return {"task": task, "search_result": result}

    pre_fetched = await asyncio.gather(
        *[_pre_fetch(t) for t in tasks],
        return_exceptions=True,
    )
    normalized_pre = [
        p if not isinstance(p, BaseException) else {"task": {}, "search_result": {"results": []}}
        for p in pre_fetched
    ]

    # ── Phase 2: Fan-out single-turn LLM analysis per lens ──
    async def _run_one(pf: dict[str, Any]) -> dict[str, Any]:
        task = pf["task"]
        lens = str(task.get("lens", ""))
        question = str(task.get("question", ""))
        search_result = pf["search_result"]

        results_list = search_result.get("results", [])
        if isinstance(results_list, list):
            snippets = "\n".join(
                f"- [{r.get('title', '')}]({r.get('url', '')}): {r.get('snippet', '')[:200]}"
                for r in results_list[:5]
            )
        else:
            snippets = str(results_list)[:2000]

        lens_config = get_lens(lens)
        if lens_config is None:
            return {"lens": lens, "error": f"Unknown lens: {lens}"}

        prompt = SUB_RESEARCH_PROMPT.format(
            lens_name=lens_config["name"],
            question=question,
            identity=lens_config["identity"],
            concerns=lens_config["concerns"],
            blind_spot=lens_config["blind_spot"],
            pre_fetched=snippets or "（无预检索结果）",
        )

        if on_status:
            on_status(f"[sub:{lens}] Analyzing…")

        try:
            raw = await asyncio.wait_for(
                _call_llm(llm_client, prompt, lens_config["temperature"], role="creative"),
                timeout=SUB_RESEARCH_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            return {
                "lens": lens,
                "lens_name": lens_config["name"],
                "error": f"Sub-agent timed out after {SUB_RESEARCH_TIMEOUT_SECONDS:g}s",
            }
        except Exception as exc:
            return {
                "lens": lens,
                "lens_name": lens_config["name"],
                "error": f"{type(exc).__name__}: {exc}",
            }

        truncated = raw[:MAX_SUB_RESULT_CHARS]
        return {
            "lens": lens,
            "lens_name": lens_config["name"],
            "question": question,
            "summary": truncated,
            "sources": [
                r.get("url", "")
                for r in (results_list if isinstance(results_list, list) else [])[:5]
                if r.get("url")
            ],
        }

    task_results = await asyncio.gather(
        *[_run_one(pf) for pf in normalized_pre],
        return_exceptions=True,
    )

    # Normalize any exceptions that escaped the inner try/except
    normalized_results: list[dict[str, Any]] = []
    for i, r in enumerate(task_results):
        if isinstance(r, BaseException):
            lens = tasks[i].get("lens", "") if i < len(tasks) else ""
            normalized_results.append({"lens": lens, "error": f"{type(r).__name__}: {r}"})
        else:
            normalized_results.append(r)

    # Build aggregated text for the main LLM's context window
    aggregated_parts: list[str] = []
    for r in normalized_results:
        if "error" in r:
            aggregated_parts.append(f"### {r.get('lens', '?')}: ERROR — {r['error']}")
        else:
            aggregated_parts.append(f"### {r['lens_name']} ({r['lens']})\n{r.get('summary', '')}")

    return {
        "task_results": normalized_results,
        "aggregated": "\n\n".join(aggregated_parts),
    }


async def fetch_and_extract(url: str) -> str:
    """Fetch an HTTP(S) page and return its readable text content."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be an absolute HTTP(S) URL")

    headers = {"User-Agent": "ResearchAgent/1.0 (+https://example.invalid)"}
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"could not fetch {url}: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    for element in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "aside"]):
        element.decompose()
    return " ".join(soup.stripped_strings)


async def web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search DuckDuckGo's HTML endpoint without requiring an API key."""
    if not query.strip():
        return []

    headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchAgent/1.0)"}
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, headers=headers) as client:
            response = await client.get("https://html.duckduckgo.com/html/", params={"q": query})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"DuckDuckGo search failed: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for item in soup.select(".result"):
        link = item.select_one("a.result__a")
        if link is None or not link.get("href"):
            continue
        snippet_node = item.select_one(".result__snippet")
        results.append(
            {
                "title": link.get_text(" ", strip=True),
                "url": urljoin("https://duckduckgo.com", link["href"]),
                "snippet": snippet_node.get_text(" ", strip=True) if snippet_node else "",
            }
        )
        if len(results) >= max(1, min(max_results, 10)):
            break
    return results


async def _call_llm(llm_client: Any, prompt: str, temperature: float, role: str = "creative") -> str:
    response = await llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        role=role,
    )
    if getattr(response, "error", None):
        return f"LLM error: {response.error}"
    return str(getattr(response, "content", response) if hasattr(response, "content") else response)
