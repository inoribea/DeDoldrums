<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/lines-~1.7K-lightgrey" alt="~1700 lines">
</p>

# 🔬 ResearchAgent

> *Design philosophy — **minimal seed, self-evolving researcher.** Don't preload knowledge, discover it.*

**ResearchAgent** is a self-evolving research agent built on [GenericAgent](https://github.com/lsdefine/GenericAgent)'s execution philosophy and a hybrid [STORM](https://arxiv.org/abs/2402.14207) multi-perspective methodology. You ask a question. The agent autonomously discovers perspectives, collects evidence, challenges its own conclusions, and synthesizes a research brief — all in ~1,700 lines of Python.

---

<a id="english"></a>

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

## 🚀 Quick Start

```bash
git clone https://github.com/inoribea/ResearchAgent.git && cd ResearchAgent
pip install -r requirements.txt          # 4 dependencies total
cp .env.example .env                     # fill in OPENAI_API_KEY

# Single research session
python main.py "What is the real timeline for quantum computing to break RSA?"

# Goal Mode — 30 minutes of continuous deep-dive
python main.py --goal --budget 30 "Comparing feasible AGI governance frameworks"
```

### Bridge Mode (multi-platform)

```bash
python bridge.py                         # http://127.0.0.1:14168
python adapters/telegram_bot.py          # optional
python adapters/discord_bot.py           # optional
```

### Vercel Frontend

```bash
cd adapters/vercel && npm install
# Set BRIDGE_URL + BRIDGE_API_KEY in Vercel dashboard
npx vercel deploy --prod
```

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
└── adapters/           # Telegram / Discord / Vercel thin adapters
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

---

<a id="-中文"></a>

# 🔬 ResearchAgent

> *设计哲学 — **极简种子，自我进化。** 不预装知识，去发现知识。*

**ResearchAgent** 是一个基于 [GenericAgent](https://github.com/lsdefine/GenericAgent) 执行哲学与混合 [STORM](https://arxiv.org/abs/2402.14207) 多视角方法论的自我进化研究 Agent。你只需提问，Agent 自主发现视角、收集证据、挑战自身结论、合成研究简报——全部在 ~1,700 行 Python 中完成。

---

## 🌟 项目简介

GenericAgent 研究**计算机**。ResearchAgent 研究**议题**。同一副骨架，不同的工具。

| GenericAgent | ResearchAgent |
|:---|:---|
| 9 个计算机控制工具 | 4 个知识操作工具 |
| 任务执行循环 | 5.5 阶段 STORM 研究管线 |
| 任务→SOP 自我进化 | 洞察→思维模式 自我进化 |
| Goal Mode: 创造→检验→改进 | Goal Mode: 探索→检验→深化 |

我们不预设"好研究长什么样"——视角从主题自身特征中动态发现，每个关键断言经过对抗闸门压力测试，突破性洞察固化为可复用思维 SOP，每次研究都在进化。

---

## 📋 核心特性

| 特性 | 说明 |
|:---|:---|
| 🧬 **自我进化** | 突破性洞察固化为 L3 思维 SOP；Goal Mode 持续深挖直到预算耗尽 |
| 🔍 **动态视角** | 从搜索结果中动态发现特定主题的分析视角——不预设固定角色（取自原始 STORM 论文） |
| ⚔️ **对抗闸门** | Stage 3.5 对每个关键发现自动挑战：逻辑漏洞、隐藏假设、缺失证据、替代解释（取自 Caesar） |
| 🗺️ **矛盾映射** | 找出视角间冲突——哪些一致（很可能为真），哪些全员沉默（整个领域的盲点） |
| 📊 **置信度评分** | 每个发现标注 1-10 分并说明理由；低置信度断言标记待验证 |
| 🧠 **L0-L4 记忆** | 元规则 → 模式索引 → 领域知识 + 图拓扑 → 思维 SOP → 会话归档 |
| 🔌 **多平台接入** | 一个 Bridge 服务器 → Telegram、Discord、Vercel Web 通过 ~100 行薄适配层接入 |

---

## 🎯 5.5 阶段研究管线

```
Stage 0   — 动态视角发现    （基于检索结果生成该主题独有的分析维度）
Stage 1   — 多视角扫描      （动态视角 + 9 透镜库兜底，独立探索）
Stage 2   — 矛盾映射        （视角冲突、共识区域、集体盲点）
Stage 3   — 综合合成        （跨视角连接 → 结构化研究简报）
Stage 3.5 — ⚔️ 对抗验证闸门  （Generator-Verifier 自动压力测试每个关键发现）
Stage 4   — 同行评审        （置信度评分 + 偏见检测 + 缺失视角）
```

> ⚠️ **Stage 3.5 是闸门，不是建议。** 每个关键发现必须挺过对抗性挑战才能进入同行评审。Verifier 发现实质性漏洞 → 修正论证 → 重新验证。未经验证的断言不得通过。

---

## 🚀 快速开始

```bash
git clone https://github.com/inoribea/ResearchAgent.git && cd ResearchAgent
pip install -r requirements.txt          # 总共 4 个依赖
cp .env.example .env                     # 填入 OPENAI_API_KEY

# 单次研究
python main.py "量子计算对 RSA 的真实威胁时间线是什么？"

# Goal Mode — 30 分钟持续深挖
python main.py --goal --budget 30 "比较可行的 AGI 治理框架"
```

### Bridge 模式（多平台接入）

```bash
python bridge.py                         # 监听 http://127.0.0.1:14168
python adapters/telegram_bot.py          # 可选
python adapters/discord_bot.py           # 可选
```

### Vercel 前端部署

```bash
cd adapters/vercel && npm install
# 在 Vercel 控制台设置 BRIDGE_URL + BRIDGE_API_KEY
npx vercel deploy --prod
```

---

## 🏗️ 架构

```
research_agent/
├── agent_loop.py       # 异步主循环（LLM 决策 → 工具调度 → 阶段推进）
├── handler.py          # 工具路由 + 5.5 阶段状态机
├── tools.py            # explore / reflect / challenge / crystallize
├── llm.py              # OpenAI 兼容客户端（httpx，零框架依赖）
├── memory.py           # L0-L4 分层记忆 + L2 图索引
├── lenses.py           # 动态视角发现 + 9 透镜库兜底
├── prompts.py          # STORM 各阶段 prompt 模板
├── goal_mode.py        # 持续自驱循环（移植自 GA）
├── main.py             # CLI 入口
├── config.py           # 环境变量配置
├── bridge.py           # aiohttp HTTP+SSE 服务器
├── launch.py           # 一键启动 bridge + bot
└── adapters/           # Telegram / Discord / Vercel 薄适配层
```

### 4 个知识工具

| 工具 | 参数 | 功能 |
|:---|:---|:---|
| `explore` | `query` + `source`（web/memory/url） | DuckDuckGo 搜索、记忆库检索、URL 深度阅读 |
| `reflect` | `lens` + `focus` | 切换思维透镜（实践者/怀疑论/经济学家/…）深度分析 |
| `challenge` | `target` + `mode` | 对抗压力测试：逻辑漏洞、隐藏假设、缺失证据、替代解释 |
| `crystallize` | `insight` + `category` | 将突破性洞察固化到分层记忆，供未来复用 |

---

## 📚 方法论

ResearchAgent 融合了三方工作：

| 来源 | 取什么 | 参考 |
|:---|:---|:---|
| **GenericAgent** | 执行框架 | [lsdefine/GenericAgent](https://github.com/lsdefine/GenericAgent) |
| **STORM（原始论文）** | 动态视角发现 | [Shao et al., NAACL 2024](https://arxiv.org/abs/2402.14207) |
| **STORM（社区衍生版）** | 4 阶段框架 + 矛盾映射 + 同行评审 | [storm-research-method](https://github.com/kamilwpaczce-svg/storm-research-method) |
| **Caesar** | Generator-Verifier 对抗循环 + 图结构知识 | Liang et al., 2026 |

> 原始 STORM 论文输出 Wikipedia 风格文章；社区衍生版发明了原始论文承认缺失的矛盾映射、同行评审、置信度评分机制。本项目进一步升级：动态视角（取原始 STORM 之长）、对抗验证闸门（取 Caesar 之长）、图结构记忆索引。

---

## 🙏 致谢

站在 [**GenericAgent**](https://github.com/lsdefine/GenericAgent) 的肩膀上——`StepOutcome`-dispatch 模式、Goal Mode 自驱循环、分层记忆设计均直接移植自 GA。它以 ~3K 行代码覆盖完整计算机控制，证明了极简路线的可行性，启发了本项目的设计哲学。

感谢 [**STORM 论文**](https://arxiv.org/abs/2402.14207)（Shao et al., NAACL 2024）提出的多视角分析突破单一视角盲点的核心洞察，以及社区衍生版发明了矛盾映射与同行评审机制。

感谢 **Caesar**（Liang et al., 2026）的 Generator-Verifier 对抗验证框架，直接成为 Stage 3.5 闸门的设计基础。

---

## 📄 许可

[MIT](LICENSE)
