<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/deps-4-lightgrey" alt="4 dependencies">
</p>

<p align="center">
  <a href="README.md">📖 English</a>
</p>

# DeDoldrums

> **Know your shore by storm.**
>
> *The streaked shearwater survives typhoons not by bravery, but by bearings.*
>
> **Don't flee uncertainty. Don't chase it. Navigate it—with the shore in mind.**

一个将冲突视角淬炼为经得起检验的洞见、以方位感而非蛮勇穿越分歧的研究 Agent。

基于 [GenericAgent](https://github.com/lsdefine/GenericAgent) 构建，受 [STORM](https://arxiv.org/abs/2402.14207) 启发。

成年白额鹱能够判断陆地的方位，缺乏这种方位感的幼鸟更容易在风暴后迷航。DeDoldrums 为议题建立同样的方位感：先画出矛盾地图，再选择审慎的航线。

---

## 与同类有何不同

大多数研究 Agent 止步于「搜索 → 摘要 → 引用」。DeDoldrums 多了两样东西：

| 不同之处 | 为什么重要 |
|:---|:---|
| **强制对抗闸门** | 综合合成后，管线会物理性阻断——直到至少一条关键发现通过结构化挑战（逻辑漏洞、隐藏假设、缺失证据、替代解释）。不是让模型"自己检查一下"，是硬性阻断。未通过的发现标记为需修正，随挑战结果一起进入最终简报。 |
| **角色级 LLM 路由** | 四个研究角色（`tool_calling`、`creative`、`conversational`、`content_review`）各自可以指向不同的模型和提供商。调度用 GPT-5.5，发散思维用 Claude，对抗闸门用独立模型——没有自我审查偏差。 |

底层：4.5 阶段 STORM 管线、动态视角发现、扇出并行子代理、跨会话持久化的 L0-L4 分层记忆。

---

## 研究管线

```
Stage 0   — 动态视角发现    （网络搜索 → 生成该主题特有的分析视角）
Stage 1   — 多视角扫描      （扇出并行子代理，每个视角独立研究）
Stage 2   — 矛盾映射        （冲突、共识、集体盲点）
Stage 3   — 综合合成        （跨视角连接 → 结构化简报）
Stage 3.5 — ⚔️ 对抗验证闸门  （阻断直至 ≥1 条挑战执行；最终质量闸门）
```

> Stage 3.5 不是让模型"检查一下自己的作业"。它是硬性闸门——没有 `challenge` 工具的真实调用，管线不会推进。闸门通过后直接生成最终研究简报。

---

## 特性一览

| 特性 | 说明 |
|:---|:---|
| ⚔️ **强制对抗闸门** | Stage 3.5 硬性阻断管线。4 种挑战模式并发执行：逻辑漏洞、隐藏假设、缺失证据、替代解释。标记发现随挑战结果流入后续阶段。 |
| 🎭 **多角色 LLM** | 4 个角色独立路由到不同模型/提供商。杜绝单模型自我审查。 |
| 🔌 **多提供商** | 5 种 API 后端（chat / responses / messages / completions / v1beta）× 7 个提供商（OpenAI、Anthropic、DeepSeek、Kimi、智谱、Google、OpenAI 兼容）。纯 HTTP——无 SDK 锁定。 |
| ⚡ **扇出并行** | Stage 1 通过 `asyncio.gather` 并发调度 2-3 个透镜子代理。每个子代理独立预取搜索结果、运行 LLM 分析、返回汇总。 |
| 🔍 **动态视角** | 从实时搜索结果中发现该主题特有的分析视角——不同于固定视角方案，每个视角为当前议题量身生成，并可作为一等公民工具身份在管线中使用。9 透镜静态库兜底。 |
| 🧠 **L0-L4 记忆** | 分层扁平文件记忆：元规则 → 模式索引 → 领域知识 → 思维 SOP → 会话归档。无向量数据库。洞察跨会话结晶复用。 |
| 🗺️ **矛盾映射** | 在得出结论之前，先找出各视角在哪里一致、哪里冲突、哪里共享盲点。 |
| 🧍 **人工检查点** | 对抗闸门后、最终简报前可选暂停，展示矛盾地图、综合结果与审计缺口。可通过 `--no-human-gate` 关闭。 |
| 🌐 **多平台接入** | 一个 aiohttp bridge 同时服务 HTTP+SSE → Web UI（Next.js 14）、Telegram bot、Discord bot、Vercel 代理。 |

---

## 快速开始

```bash
git clone https://github.com/inoribea/DeDoldrums.git && cd DeDoldrums
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                      # 总共 4 个依赖
cp .env.example .env
```

### CLI

```bash
python main.py "量子计算对 RSA 的真实威胁时间线是什么？"
python main.py --goal --budget 30 "比较可行的 AGI 治理框架"
```

### Web UI

```bash
python bridge.py                     # → http://127.0.0.1:18765
```

实时管线可视化、可折叠思考日志、流式输出。

### Docker

```bash
docker compose up -d                 # → http://localhost:18765
```

`docker-compose.yml` 将 `./memory/` 挂载为卷——知识在重启后持续保留。

### LLM 配置

每个研究角色可独立使用不同模型/提供商。格式：`提供商/模型ID`。

```bash
LLM_TOOL_CALLING=openai/gpt-5.5              # 管线调度，工具选择
LLM_CREATIVE=anthropic/claude-sonnet-5       # 视角发现，发散思维
LLM_CONVERSATIONAL=openai/gpt-5.5-mini       # 用户交互，最终简报
LLM_CONTENT_REVIEW=openai/gpt-5.5            # 对抗闸门，挑战执行
```

---

## 知识工具

| 工具 | 功能 |
|:---|:---|
| `explore` | DuckDuckGo 搜索、记忆检索、URL 深度阅读 |
| `reflect` | 应用思维透镜（动态或静态）分析已有发现 |
| `challenge` | 4 模式对抗压力测试——逻辑、假设、证据、替代解释——并发执行 |
| `crystallize` | 将突破性洞察固化到分层记忆，供跨会话复用 |
| `sub_research` | 扇出并行子代理：按透镜预取搜索、并发单轮 LLM 分析；每个任务返回 ≤10 条（claim, source_url, confidence）三元组 |
| `document_audit` | 闸门通过前按 5 项指标（来源可定位、反证、诚实盲点、标签正确、覆盖度）对文档进行审计 |

---

## 架构

```
├── agent_loop.py       # 异步主循环（LLM → 调度 → 阶段推进）
├── handler.py          # 工具路由 + 4.5 阶段状态机
├── tools.py            # explore / reflect / challenge / crystallize / sub_research / document_audit
├── llm.py              # 5 种后端 × 7 提供商，角色级 LLMRouter
├── memory.py           # L0-L4 分层扁平文件记忆
├── lenses.py           # 动态视角发现 + 9 透镜静态库
├── prompts.py          # STORM 各阶段 prompt 模板（中文）
├── goal_mode.py        # 预算感知的自驱深化循环
├── main.py             # CLI 入口
├── config.py           # 角色级 LLM 配置 + 提供商解析
├── bridge.py           # aiohttp HTTP+SSE 服务器 + 静态前端托管
├── launch.py           # 一键启动 bridge + Telegram/Discord bot
├── adapters/           # Telegram / Discord bot 适配层
├── vercel/             # Next.js 14 + shadcn/ui 前端 + API 代理路由
├── Dockerfile / docker-compose.yml / systemd/
└── tests/              # 管线、工具、闸门行为
```

---

## 方法论

| 来源 | 继承了什么 | 新增了什么 |
|:---|:---|:---|
| **GenericAgent** | 执行框架、Goal Mode、分层记忆骨架 | 研究专用工具、知识域记忆层（L1-L3） |
| **STORM**（Shao et al., NAACL 2024） | 多视角研究框架 | 动态视角发现（从搜索生成而非预定义）、透镜一等公民工具身份、强制对抗闸门、扇出子代理 |
| **STORM 社区衍生版** | 矛盾映射、同行评审机制 | 与对抗闸门的紧密集成——被标记的发现直接进入最终简报（独立的同行评审阶段已移除，由闸门取代） |
| **Caesar**（Liang et al., 2026） | Generator-Verifier 对抗循环概念 | 硬性闸门管线强制——循环阻断，而非仅建议 |

---

## 🙏 致谢

站在 [**GenericAgent**](https://github.com/lsdefine/GenericAgent) 的肩膀上——`StepOutcome`-dispatch 模式、Goal Mode 自驱循环、分层记忆设计均直接移植自 GA。

感谢 [**STORM 论文**](https://arxiv.org/abs/2402.14207)（Shao et al., NAACL 2024）的多视角研究框架，启发了我们的动态透镜方案；以及[社区衍生版](https://github.com/kamilwpaczce-svg/storm-research-method)的矛盾映射与同行评审机制。

感谢 **Caesar**（Liang et al., 2026）的 Generator-Verifier 对抗框架，启发了闸门设计。

---

## 许可

[MIT](LICENSE)
