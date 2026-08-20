<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/deps-4-lightgrey" alt="4 dependencies">
</p>

<p align="center">
  <a href="README_zh.md">📖 中文文档</a>
</p>

# DeDoldrums

> **Know your shore by storm.**
>
> *The streaked shearwater survives typhoons not by bravery, but by bearings.*
>
> **Don't flee uncertainty. Don't chase it. Navigate it—with the shore in mind.**

A research agent that turns conflicting perspectives into tested insight — navigating disagreement with bearings, not bravado.

Built on [GenericAgent](https://github.com/lsdefine/GenericAgent) and inspired by [STORM](https://arxiv.org/abs/2402.14207).

Research suggests that adult streaked shearwaters hold a map sense of where land lies; juveniles, lacking it, are disproportionately wrecked after storms. DeDoldrums builds that map sense for a topic: contradiction maps first, deliberate passage second.

---

## What Makes It Different

Most research agents stop at "search → summarize → cite." DeDoldrums adds two things:

| What | Why It Matters |
|:---|:---|
| **Enforced adversarial gate** | The pipeline physically blocks after synthesis until at least one finding passes a structured challenge — logic flaws, hidden assumptions, missing evidence, alternative explanations. No rubber-stamping. Findings that fail are flagged for revision and carried into the final brief. |
| **Role-based LLM routing** | Four research roles (`tool_calling`, `creative`, `conversational`, `content_review`) can each use a different model and provider. Your orchestrator runs on GPT-5.5 while divergent thinking uses Claude. The adversarial gate gets its own model — no self-review bias. |

Under the hood: a 4.5-stage STORM pipeline, dynamic perspective discovery, fan-out parallel sub-agents, and L0-L4 layered memory that persists insights across sessions.

---

## The Pipeline

```
Stage 0   — Dynamic Lens Discovery    (web search → generate topic-specific perspectives)
Stage 1   — Multi-Perspective Scan    (fan-out parallel sub-agents, one per lens)
Stage 2   — Contradiction Map         (conflicts, consensus, collective blind spots)
Stage 3   — Synthesis                 (cross-lens connections → structured brief)
Stage 3.5 — ⚔️ Adversarial Gate       (blocks until ≥1 challenge executed; final quality gate)
```

> Stage 3.5 is not a prompt asking the model to "check your work." It's a hard gate — the loop won't proceed until the `challenge` tool has been called with actual analysis, not a summary. After the gate passes, the pipeline generates the final research brief directly.

---

## Feature Overview

| Feature | Description |
|:---|:---|
| ⚔️ **Enforced Adversarial Gate** | Stage 3.5 hard-blocks the pipeline. 4 challenge modes run concurrently: logic flaws, hidden assumptions, missing evidence, alternative explanations. Flagged findings carry forward. |
| 🎭 **Multi-Role LLM** | 4 roles independently routed to different models/providers. No single-model self-review. |
| 🔌 **Multi-Provider** | 5 API backends (chat / responses / messages / completions / v1beta) × 7 providers (OpenAI, Anthropic, DeepSeek, Kimi, Zhipu, Google, OpenAI-compatible). Raw HTTP — no SDK lock-in. |
| ⚡ **Fan-Out Parallelism** | Stage 1 dispatches 2-3 lens sub-agents concurrently via `asyncio.gather`. Each sub-agent pre-fetches its own web search, runs independent LLM analysis, then returns. |
| 🔍 **Dynamic Perspectives** | Discovers topic-specific lenses from live search results — unlike fixed-perspective approaches, each lens is generated for the topic at hand and usable as a first-class tool identity in the pipeline. 9-lens static library as fallback. |
| 🧠 **L0-L4 Memory** | Layered flat-file memory: meta-rules → pattern index → domain knowledge → thinking SOPs → session archives. No vector DB. Insights crystallize across sessions. |
| 🗺️ **Contradiction Mapping** | Surfaces where perspectives agree, clash, or share blind spots — before conclusions are drawn. |
| 🧍 **Human Checkpoint** | Optional pause after the adversarial gate, before the final brief, showing the contradiction map + synthesis + audit gaps. Disabled via `--no-human-gate`. |
| 🌐 **Multi-Platform** | One aiohttp bridge serves HTTP+SSE → Web UI (Next.js 14), Telegram bot, Discord bot, Vercel proxy. |

---

## Quick Start

```bash
git clone https://github.com/inoribea/DeDoldrums.git && cd DeDoldrums
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                      # 4 dependencies total
cp .env.example .env
```

### CLI

```bash
python main.py "What is the real timeline for quantum computing to break RSA?"
python main.py --goal --budget 30 "Comparing feasible AGI governance frameworks"
```

### Web UI

```bash
python bridge.py                     # → http://127.0.0.1:18765
```

Live pipeline visualization, collapsible thinking log, streaming output.

### Docker

```bash
docker compose up -d                 # → http://localhost:18765
```

The `docker-compose.yml` mounts `./memory/` as a volume — knowledge persists across restarts.

### LLM Configuration

Each research role routes to a different model. Format: `PROVIDER/MODEL_ID`.

```bash
LLM_TOOL_CALLING=openai/gpt-5.5              # pipeline orchestration, tool selection
LLM_CREATIVE=anthropic/claude-sonnet-5       # lens discovery, divergent thinking
LLM_CONVERSATIONAL=openai/gpt-5.5-mini       # user interaction, final report
LLM_CONTENT_REVIEW=openai/gpt-5.5            # adversarial gate, challenge execution
```

---

## Knowledge Tools

| Tool | Does |
|:---|:---|
| `explore` | DuckDuckGo search, memory retrieval, URL deep reading |
| `reflect` | Apply a thinking lens (dynamic or static) to analyze findings |
| `challenge` | 4-mode adversarial pressure test — logic, assumptions, evidence, alternatives — runs concurrently |
| `crystallize` | Persist breakthrough insights into layered memory for cross-session reuse |
| `sub_research` | Fan-out parallel sub-agents: pre-fetch search per lens, concurrent single-turn LLM analysis; returns ≤10 (claim, source_url, confidence) triples per task |
| `document_audit` | Document-level audit against a 6-point rubric (source locatability, counterevidence, honest blind spots, correct labels, coverage, and claim-source support) before the gate passes. Each claim is classified as supported, weakly supported, unsupported, wrong source, or missing source. |

---

## Architecture

```
├── agent_loop.py       # async main loop (LLM → dispatch → stage advance)
├── handler.py          # tool router + 4.5-stage state machine
├── tools.py            # explore / reflect / challenge / crystallize / sub_research / document_audit
├── llm.py              # 5 backends × 7 providers, role-based LLMRouter
├── memory.py           # L0-L4 layered flat-file memory
├── lenses.py           # dynamic lens discovery + 9-lens static library
├── prompts.py          # STORM stage prompt templates (Chinese)
├── goal_mode.py        # budget-aware self-driven deepening loop
├── main.py             # CLI entry
├── config.py           # role-based LLM config + provider resolution
├── bridge.py           # aiohttp HTTP+SSE server + static frontend hosting
├── launch.py           # one-click: bridge + Telegram/Discord bots
├── adapters/           # Telegram / Discord bot adapters
├── vercel/             # Next.js 14 + shadcn/ui frontend + API proxy routes
├── Dockerfile / docker-compose.yml / systemd/
└── tests/              # pipeline, tools, gate behavior
```

---

## Methodology

| Source | What We Inherited | What We Added |
|:---|:---|:---|
| **GenericAgent** | Execution framework, Goal Mode, layered memory skeleton | Research-specific tools, knowledge-domain memory layers (L1-L3) |
| **STORM** (Shao et al., NAACL 2024) | Multi-perspective research framework | Dynamic lens discovery (generated from search, not pre-defined), first-class tool identities for lenses, enforced adversarial gate, fan-out sub-agents |
| **Co-STORM** (Jiang et al., EMNLP 2024) | Human-in-the-loop participation and steering in multi-perspective research | Human Checkpoint — an optional post-gate pause where a human reviews contradiction map, synthesis, and audit gaps before the final brief |
| **STORM community** | Contradiction mapping, peer review mechanisms | Tight integration with adversarial gate — flagged findings carry into the final brief (the separate peer-review stage was removed in favor of the gate) |
| **Caesar** (Liang et al., 2026) | Generator-Verifier adversarial loop concept | Hard-gated pipeline enforcement — the loop blocks, not just suggests |

---

## Convergent Validation from Independent Research

The following 2026 arXiv preprints identify failure modes and design targets that align with mechanisms already defined in DeDoldrums (P1-P8). They are cited as convergent evidence, not as implementation sources — DeDoldrums does not inherit or implement code, frameworks, or evaluation pipelines from these works.

| Preprint | Key Alignment |
|:---|:---|
| [**From Fluent to Verifiable**](https://arxiv.org/abs/2602.13855) (Rasheed et al., 2026 preprint) | Aligns with P2/P5/P6/P8: treats provenance coverage, provenance soundness, and contradiction transparency as first-class audit targets for deep research agents. |
| [**Cited but Not Verified**](https://arxiv.org/abs/2605.06635) (Onweller et al., 2026 preprint) | Aligns with P1/P2/P5: evaluates source attribution through link accessibility, topical relevance, and fact checking; shows that surface-level citation quality does not imply factual reliability. |
| [**AutoResearch**](https://arxiv.org/abs/2607.02520) (Kumar et al., 2026 preprint) | Aligns with P2/P4/P8: uses citation verification and claim-support auditing as runtime filtering signals in a multi-agent research workflow. |

---

## 🙏 Acknowledgments

Built on the shoulders of [**GenericAgent**](https://github.com/lsdefine/GenericAgent) — the `StepOutcome`-dispatch pattern, Goal Mode self-driven loop, and layered memory design are directly ported from GA.

Thanks to the [**STORM paper**](https://arxiv.org/abs/2402.14207) (Shao et al., NAACL 2024) for the multi-perspective research framework that inspired our dynamic lens approach, and the [community fork](https://github.com/kamilwpaczce-svg/storm-research-method) for contradiction mapping and peer review mechanisms.

Thanks to [**Co-STORM**](https://arxiv.org/abs/2408.15232) (Jiang et al., EMNLP 2024, Stanford OVAL) for demonstrating that human participation and steering make multi-perspective research more trustworthy — the inspiration for our optional Human Checkpoint.

Thanks to **Caesar** (Liang et al., 2026) for the Generator-Verifier adversarial framework that inspired the gate design.

---

## License

[MIT](LICENSE)
