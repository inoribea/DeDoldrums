<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/lines-~1.7K-lightgrey" alt="~1700 lines">
  <a href="README_zh.md">中文</a>
</p>

# 🔬 ResearchAgent

> *Design philosophy — **minimal seed, self-evolving researcher.** Don't preload knowledge, discover it.*

**ResearchAgent** is a self-evolving research agent built on [GenericAgent](https://github.com/lsdefine/GenericAgent)'s execution philosophy and a hybrid [STORM](https://arxiv.org/abs/2402.14207) multi-perspective methodology. You ask a question. The agent autonomously discovers perspectives, collects evidence, challenges its own conclusions, and synthesizes a research brief — all in ~1,700 lines of Python.

---

## 🌟 Overview

A GenericAgent studies **computers**. A ResearchAgent studies **topics**. Same skeleton, different tools.

| GenericAgent | ResearchAgent |
|:---|:---|
| 9 computer-control tools (`code_run`, `web_scan`, `file_read`…) | 4 knowledge-operation tools (`explore`, `reflect`, `challenge`, `crystallize`) |
| Task execution loop | 5.5-stage STORM research pipeline |
| Self-evolves via task→SOP | Self-evolves via insight→thinking pattern |
| Goal Mode: create→verify→improve | Goal Mode: explore→verify→deepen |

Instead of preloading "what a good research looks like," ResearchAgent discovers perspectives dynamically, stress-tests every finding through an adversarial gate, and crystallizes breakthroughs into reusable thinking SOPs — growing smarter with every session.

---

## 📋 Key Features

| Feature | Description |
|:---|:---|
| 🧬 **Self-Evolving** | Crystallizes breakthrough insights into L3 thinking SOPs; Goal Mode keeps digging until budget runs out |
| 🔍 **Dynamic Perspectives** | Discovers topic-specific lenses from search results — not hardcoded roles (from original STORM paper) |
| ⚔️ **Adversarial Gate** | Stage 3.5 auto-challenges every key finding: logic flaws, hidden assumptions, missing evidence, alternative explanations (from Caesar) |
| 🗺️ **Contradiction Mapping** | Surfaces conflicts between perspectives — where they agree (likely true), where they're all silent (biggest blind spots) |
| 📊 **Confidence Scoring** | Every finding rated 1-10 with explicit reasoning; weak claims flagged for follow-up |
| 🧠 **L0-L4 Memory** | Meta-rules → pattern index → domain knowledge + graph edges → thinking SOPs → session archives |
| 🔌 **Multi-Platform** | One Bridge server → Telegram, Discord, Vercel Web through ~100-line adapters |

---

## 🎯 The 5.5-Stage Pipeline

```
Stage 0   — Dynamic Lens Discovery    (topic-specific perspectives via search)
Stage 1   — Multi-Perspective Scan    (5 lenses × independent exploration)
Stage 2   — Contradiction Map         (conflicts, consensus, blind spots)
Stage 3   — Synthesis                 (cross-lens connections → structured brief)
Stage 3.5 — ⚔️ Adversarial Gate       (Generator-Verifier pressure test on every finding)
Stage 4   — Peer Review               (confidence scores, bias check, missing angles)
```

> ⚠️ **Stage 3.5 is a gate — not a suggestion.** Every key finding must survive adversarial challenge before entering peer review. If Verifier finds substantive flaws → fix → re-verify. No unverified claims make it through.

---

## 🚀 Local Deployment

### Option A: Bare Metal (Python venv)

```bash
git clone https://github.com/inoribea/ResearchAgent.git && cd ResearchAgent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                      # 4 dependencies total
cp .env.example .env                                 # fill in OPENAI_API_KEY
```

**CLI mode** — single research session:

```bash
python main.py "What is the real timeline for quantum computing to break RSA?"
python main.py --goal --budget 30 "Comparing feasible AGI governance frameworks"
```

**Web UI mode** — full research station with built-in frontend:

```bash
python bridge.py                     # → http://127.0.0.1:14168
```

Open your browser. Type a question. Watch the 5.5-stage pipeline in real time. No Vercel, no external services — the bridge serves the web frontend directly.

**With bots** (optional):

```bash
export TELEGRAM_BOT_TOKEN="..."      # optional
export DISCORD_BOT_TOKEN="..."       # optional
python launch.py                      # starts bridge + all configured bots
```

### Option B: Docker (recommended for servers)

```bash
git clone https://github.com/inoribea/ResearchAgent.git && cd ResearchAgent
cp .env.example .env                 # fill in OPENAI_API_KEY
docker compose up -d                 # → http://localhost:14168
```

The `docker-compose.yml` mounts `./memory/` as a volume — your agent's knowledge persists across restarts.

### Option C: systemd (Linux servers)

```bash
sudo cp systemd/research-agent.service /etc/systemd/system/
sudo useradd -r -s /bin/false research
sudo mkdir -p /opt/research-agent
sudo cp -r . /opt/research-agent/
sudo cp .env /opt/research-agent/
cd /opt/research-agent && python -m venv .venv && .venv/bin/pip install -r requirements.txt
sudo systemctl daemon-reload
sudo systemctl enable --now research-agent    # → http://your-server:14168
```

### LLM Provider Configuration

Edit `.env` — any OpenAI-compatible provider works:

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# Azure OpenAI
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://YOUR_RESOURCE.openai.azure.com/openai/deployments/YOUR_DEPLOYMENT

# Local (ollama / vllm / LM Studio)
OPENAI_API_KEY=not-needed
OPENAI_BASE_URL=http://localhost:11434/v1    # ollama default
```

### Vercel Frontend (public access, no server needed)

```bash
cd vercel && npm install
# Set BRIDGE_URL + BRIDGE_API_KEY in Vercel dashboard
npx vercel deploy --prod
```

The Vercel Edge Functions proxy SSE to your bridge — users access the web UI without touching your server directly.

---

## 🏗️ Architecture

```
research_agent/
├── agent_loop.py       # async main loop (LLM → dispatch → stage advance)
├── handler.py          # tool router + 5.5-stage state machine
├── tools.py            # explore / reflect / challenge / crystallize
├── llm.py              # OpenAI-compatible client (httpx, zero framework deps)
├── memory.py           # L0-L4 layered memory + L2 graph index
├── lenses.py           # dynamic lens discovery + 9-lens fallback library
├── prompts.py          # STORM stage prompt templates
├── goal_mode.py        # continuous self-driven loop (ported from GA)
├── main.py             # CLI entry
├── config.py           # env-based config
├── bridge.py           # aiohttp HTTP+SSE server
├── launch.py           # one-click: bridge + bots
├── adapters/           # Telegram / Discord bot adapters
└── vercel/             # Vercel Edge Functions + web frontend
```

### The 4 Knowledge Tools

| Tool | Schema | Does |
|:---|:---|:---|
| `explore` | `query` + `source` (web/memory/url) | DuckDuckGo search, local memory search, deep URL reading |
| `reflect` | `lens` + `focus` | Applies a thinking lens (practitioner/skeptic/economist/...) to analyze findings |
| `challenge` | `target` + `mode` | Adversarial pressure test: logic flaws, hidden assumptions, missing evidence, alternatives |
| `crystallize` | `insight` + `category` | Persists breakthrough patterns into layered memory for future reuse |

---

## 📚 Methodology

ResearchAgent fuses three lines of work:

| Source | What We Took | Reference |
|:---|:---|:---|
| **GenericAgent** | Execution framework | [lsdefine/GenericAgent](https://github.com/lsdefine/GenericAgent) |
| **STORM (original)** | Dynamic perspective discovery | [Shao et al., NAACL 2024](https://arxiv.org/abs/2402.14207) |
| **STORM (community)** | 4-stage framework + contradiction mapping + peer review | [storm-research-method](https://github.com/kamilwpaczce-svg/storm-research-method) |
| **Caesar** | Generator-Verifier adversarial loop + graph-structured knowledge | Liang et al., 2026 |

> The original STORM paper outputs Wikipedia-style articles. The community fork invented contradiction mapping, peer review, and confidence scoring — mechanisms the original paper acknowledged as missing. This project goes further: dynamic lenses (from original STORM), adversarial gate (from Caesar), graph-indexed memory.

---

## 🙏 Acknowledgments

Built on the shoulders of [**GenericAgent**](https://github.com/lsdefine/GenericAgent) — the `StepOutcome`-dispatch pattern, Goal Mode self-driven loop, and layered memory design are directly ported from GA. Its proof that ~3K lines can cover full computer control inspired this project's minimalist approach.

Thanks to the [**STORM paper**](https://arxiv.org/abs/2402.14207) (Shao et al., NAACL 2024) for the core insight of multi-perspective analysis breaking single-viewpoint blindness, and the community fork for inventing the contradiction-mapping + peer-review mechanisms.

Thanks to **Caesar** (Liang et al., 2026) for the Generator-Verifier adversarial framework that became Stage 3.5.

---

## 📄 License

[MIT](LICENSE)
