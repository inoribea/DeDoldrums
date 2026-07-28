<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/lines-~2.5K-lightgrey" alt="~2500 lines">
</p>

<p align="center">
  <a href="README_zh.md">📖 中文文档</a>
</p>

# DeDoldrums

> **Break the doldrums.**  
> *Fly like a streaked shearwater—toward the eye of the storm.*  
> **Don't merely weather uncertainty. Follow it to discovery.**

A self-evolving research agent that turns conflicting perspectives into tested insight.

Built on [GenericAgent](https://github.com/lsdefine/GenericAgent) and inspired by [STORM](https://arxiv.org/abs/2402.14207).

---

## 🌟 Overview

A GenericAgent studies **computers**. A DeDoldrums studies **topics**. Same skeleton, different tools.

| GenericAgent | DeDoldrums |
|:---|:---|
| 9 computer-control tools | 4 knowledge-operation tools (`explore`, `reflect`, `challenge`, `crystallize`) |
| Task execution loop | 5.5-stage STORM research pipeline |
| Self-evolves via task→SOP | Self-evolves via insight→thinking pattern |
| Goal Mode: create→verify→improve | Goal Mode: explore→verify→deepen |

Instead of preloading "what good research looks like," DeDoldrums discovers perspectives dynamically from web search results, stress-tests every finding through an enforced adversarial gate, and crystallizes breakthroughs into reusable thinking SOPs.

---

## 📋 Key Features

| Feature | Description |
|:---|:---|
| 🧬 **Self-Evolving** | Crystallizes insights into L3 thinking SOPs; Goal Mode deepens across iterations with prior context |
| 🔍 **Dynamic Perspectives** | Discovers topic-specific lenses from search results — usable as first-class lens identities |
| ⚔️ **Adversarial Gate** | Stage 3.5 requires real challenge calls; findings with detected issues are marked for revision |
| 🗺️ **Contradiction Mapping** | Surfaces conflicts between perspectives — consensus zones and collective blind spots |
| 🎭 **Multi-Role LLM** | Four roles (conversational, tool_calling, creative, content_review) each routed to different models/backends |
| 🔌 **Multi-Provider** | 5 backends (chat / responses / messages / completions / v1beta) × 7 providers (OpenAI, Anthropic, DeepSeek, Kimi, Zhipu, Google, OpenAI-Completion) |
| 🧠 **L0-L4 Memory** | Meta-rules → pattern index → domain knowledge → thinking SOPs → session archives |
| 🌐 **Multi-Platform** | One Bridge server → Web UI, Telegram, Discord, Vercel |

---

## 🎯 The 5.5-Stage Pipeline

```
Stage 0   — Dynamic Lens Discovery    (web search → LLM → topic-specific perspectives)
Stage 1   — Multi-Perspective Scan    (dynamic lenses × independent exploration)
Stage 2   — Contradiction Map         (conflicts, consensus, blind spots)
Stage 3   — Synthesis                 (cross-lens connections → structured brief)
Stage 3.5 — ⚔️ Adversarial Gate       (enforced challenge — requires ≥1 finding examined)
Stage 4   — Peer Review               (confidence scores, bias check, missing angles)
```

> ⚠️ **Stage 3.5 requires real challenges.** The gate won't advance until findings have been examined. No rubber-stamping.

---

## 🚀 Local Deployment

### Option A: Bare Metal (Python venv)

```bash
git clone https://github.com/inoribea/DeDoldrums.git && cd DeDoldrums
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                      # 4 dependencies total
cp .env.example .env                                 # configure LLM roles
```

**CLI mode:**

```bash
python main.py "What is the real timeline for quantum computing to break RSA?"
python main.py --goal --budget 30 "Comparing feasible AGI governance frameworks"
```

**Web UI mode:**

```bash
python bridge.py                     # → http://127.0.0.1:18765
```

Open your browser. Type a question. Watch the 5.5-stage pipeline with live status and a collapsible thinking log.

### Option B: Docker

```bash
git clone https://github.com/inoribea/DeDoldrums.git && cd DeDoldrums
cp .env.example .env
docker compose up -d                 # → http://localhost:18765
```

The `docker-compose.yml` mounts `./memory/` as a volume — knowledge persists across restarts.

### Option C: systemd (Linux)

```bash
sudo cp systemd/research-agent.service /etc/systemd/system/
sudo useradd -r -s /bin/false research
sudo mkdir -p /opt/research-agent && sudo cp -r . /opt/research-agent/
sudo cp .env /opt/research-agent/
cd /opt/research-agent && python -m venv .venv && .venv/bin/pip install -r requirements.txt
sudo systemctl daemon-reload && sudo systemctl enable --now research-agent
```

### LLM Configuration

Each research role can use a different model/provider. Format: `PROVIDER/MODEL_ID`.

```bash
LLM_TOOL_CALLING=openai/gpt-5.5              # core loop, tool selection & pipeline orchestration
LLM_CREATIVE=anthropic/claude-sonnet-5       # divergent thinking, lens discovery & reflection
LLM_CONVERSATIONAL=openai/gpt-5.5-mini       # user interaction, question refinement & final report
LLM_CONTENT_REVIEW=openai/gpt-5.5            # adversarial gate, challenge & verification

# Provider API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
KIMI_API_KEY=sk-...
```

### Vercel Frontend

```bash
cd vercel && npm install
# Set BRIDGE_URL + BRIDGE_API_KEY in Vercel dashboard
npx vercel deploy --prod
```

The frontend polls the bridge through Vercel API routes every 2 seconds — no direct connection needed.

---

## 🏗️ Architecture

```
research_agent/
├── agent_loop.py       # async main loop (LLM → dispatch → stage advance)
├── handler.py          # tool router + 5.5-stage state machine
├── tools.py            # explore / reflect / challenge / crystallize
├── llm.py              # 5 backends + 7-provider registry + role-based LLMRouter
├── memory.py           # L0-L4 layered memory
├── lenses.py           # dynamic lens discovery + 9-lens static library
├── prompts.py          # STORM stage prompt templates
├── goal_mode.py        # continuous self-driven loop (ported from GA)
├── main.py             # CLI entry
├── config.py           # role-based LLM config + provider resolution
├── bridge.py           # aiohttp HTTP+SSE server + built-in frontend hosting
├── launch.py           # one-click: bridge + bots
├── adapters/           # Telegram / Discord bot adapters
├── vercel/             # Next.js 14 + shadcn/ui frontend + API proxy routes
├── Dockerfile          # containerized deployment
├── docker-compose.yml  # one-command Docker deployment
└── systemd/            # systemd service template
```

### The 4 Knowledge Tools

| Tool | Schema | Does |
|:---|:---|:---|
| `explore` | `query` + `source` (web/memory/url) | DuckDuckGo search, memory retrieval, URL deep reading |
| `reflect` | `lens` + `focus` | Applies a thinking lens (dynamic or static) to analyze findings |
| `challenge` | `target` + `mode` | Adversarial pressure test: logic, assumptions, evidence, alternatives |
| `crystallize` | `insight` + `category` | Persists breakthroughs into layered memory for future sessions |

---

## 📚 Methodology

DeDoldrums fuses four lines of work:

| Source | What We Took | Reference |
|:---|:---|:---|
| **GenericAgent** | Execution framework (StepOutcome, dispatch, Goal Mode) | [lsdefine/GenericAgent](https://github.com/lsdefine/GenericAgent) |
| **STORM (original)** | Dynamic perspective discovery | [Shao et al., NAACL 2024](https://arxiv.org/abs/2402.14207) |
| **STORM (community)** | 4-stage framework + contradiction mapping + peer review | [storm-research-method](https://github.com/kamilwpaczce-svg/storm-research-method) |
| **Caesar** | Generator-Verifier adversarial loop | Liang et al., 2026 |

> The original STORM paper outputs Wikipedia-style articles. The community fork added contradiction mapping and peer review. This project adds enforced adversarial gating and dynamic lenses that work as first-class tool identities.

---

## 🙏 Acknowledgments

Built on the shoulders of [**GenericAgent**](https://github.com/lsdefine/GenericAgent) — the `StepOutcome`-dispatch pattern, Goal Mode self-driven loop, and layered memory design are directly ported from GA.

Thanks to the [**STORM paper**](https://arxiv.org/abs/2402.14207) (Shao et al., NAACL 2024) for multi-perspective analysis, and the community fork for contradiction mapping + peer review mechanisms.

Thanks to **Caesar** (Liang et al., 2026) for the Generator-Verifier adversarial framework.

---

## 📄 License

[MIT](LICENSE)
