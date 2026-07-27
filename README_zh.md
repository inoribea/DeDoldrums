<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/lines-~1.7K-lightgrey" alt="~1700 lines">
</p>

<p align="center">
  <a href="README.md">📖 English</a>
</p>

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

## 🚀 本地部署

### 方案 A：裸机（Python venv）

```bash
git clone https://github.com/inoribea/ResearchAgent.git && cd ResearchAgent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                      # 总共 4 个依赖
cp .env.example .env                                 # 填入 OPENAI_API_KEY
```

**CLI 模式** — 单次研究会话：

```bash
python main.py "量子计算对 RSA 的真实威胁时间线是什么？"
python main.py --goal --budget 30 "比较可行的 AGI 治理框架"
```

**Web UI 模式** — 内置前端，完整研究站：

```bash
python bridge.py                     # → http://127.0.0.1:14168
```

浏览器打开即可使用。输入问题，实时观看 5.5 阶段管线推进。无需 Vercel，无需外部服务——bridge 直接提供前端页面。

**带机器人**（可选）：

```bash
export TELEGRAM_BOT_TOKEN="..."      # 可选
export DISCORD_BOT_TOKEN="..."       # 可选
python launch.py                      # 启动 bridge + 所有已配置的 bot
```

### 方案 B：Docker（推荐服务器部署）

```bash
git clone https://github.com/inoribea/ResearchAgent.git && cd ResearchAgent
cp .env.example .env                 # 填入 OPENAI_API_KEY
docker compose up -d                 # → http://localhost:14168
```

`docker-compose.yml` 将 `./memory/` 挂载为卷——Agent 的知识在重启后持续保留。

### 方案 C：systemd（Linux 服务器）

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

### LLM 提供商配置

编辑 `.env`——任何兼容 OpenAI 接口的提供商均可使用：

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# Azure OpenAI
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://YOUR_RESOURCE.openai.azure.com/openai/deployments/YOUR_DEPLOYMENT

# 本地模型（ollama / vllm / LM Studio）
OPENAI_API_KEY=not-needed
OPENAI_BASE_URL=http://localhost:11434/v1    # ollama 默认
```

### Vercel 前端部署（公网访问，无需自有服务器）

```bash
cd vercel && npm install
# 在 Vercel 控制台设置 BRIDGE_URL + BRIDGE_API_KEY
npx vercel deploy --prod
```

Vercel Edge Function 将 SSE 代理到你的 bridge——用户无需直连你的服务器即可使用 Web UI。

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
├── adapters/           # Telegram / Discord bot 适配层
└── vercel/             # Vercel Edge Functions + Web 前端
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
