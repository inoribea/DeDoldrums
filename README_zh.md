<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/lines-~2.5K-lightgrey" alt="~2500 lines">
</p>

<p align="center">
  <a href="README.md">📖 English</a>
</p>

# DeDoldrums

> **Know your shore by storm.**  
> *The streaked shearwater survives typhoons not by bravery, but by bearings.*  
> **Don't flee uncertainty. Don't chase it. Navigate it—with the shore in mind.**

一个将冲突视角淬炼为经得起检验的洞见、以方位感而非蛮勇穿越分歧的自我进化研究 Agent。

基于 [GenericAgent](https://github.com/lsdefine/GenericAgent) 构建，受 [STORM](https://arxiv.org/abs/2402.14207) 启发。

---

## 🌟 项目简介

GenericAgent 研究**计算机**。DeDoldrums 研究**议题**。同一副骨架，不同的工具。

| GenericAgent | DeDoldrums |
|:---|:---|
| 9 个计算机控制工具 | 4 个知识操作工具 |
| 任务执行循环 | 5.5 阶段 STORM 研究管线 |
| 任务→SOP 自我进化 | 洞察→思维模式 自我进化 |
| Goal Mode: 创造→检验→改进 | Goal Mode: 探索→检验→深化 |

我们不预设"好研究长什么样"——视角从网络搜索结果中动态发现，每个关键断言经过强制对抗闸门压力测试，突破性洞察固化为可复用思维 SOP。成年条纹鹱能够判断陆地的方位，缺乏这种方位感的幼鸟更容易在风暴后迷航；DeDoldrums 为议题建立同样的方位感：先画出矛盾地图，再选择审慎的航线。

---

## 📋 核心特性

| 特性 | 说明 |
|:---|:---|
| 🧬 **自我进化** | 突破性洞察固化为 L3 思维 SOP；Goal Mode 携带前次简报迭代深挖 |
| 🔍 **动态视角** | 从搜索结果中动态发现特定主题的分析视角——可作为一等公民反射使用 |
| ⚔️ **对抗闸门** | Stage 3.5 要求真实 challenge 调用；发现问题的断言标记为需修正 |
| 🗺️ **矛盾映射** | 找出视角间冲突——共识区域和集体盲点 |
| 🎭 **多角色 LLM** | 四种角色（对话/工具调度/创意发散/内容审查），每种独立配置模型 |
| 🔌 **多提供商** | 5 种后端（chat / responses / messages / completions / v1beta）× 7 个提供商 |
| 🧠 **L0-L4 记忆** | 元规则 → 模式索引 → 领域知识 → 思维 SOP → 会话归档 |
| 🌐 **多平台接入** | 一个 Bridge 服务器 → Web UI、Telegram、Discord、Vercel |

---

## 🎯 5.5 阶段研究管线

```
Stage 0   — 动态视角发现    （网络搜索 → LLM → 主题特定分析维度）
Stage 1   — 多视角扫描      （动态视角 × 独立探索）
Stage 2   — 矛盾映射        （视角冲突、共识区域、集体盲点）
Stage 3   — 综合合成        （跨视角连接 → 结构化简报）
Stage 3.5 — ⚔️ 对抗验证闸门  （强制 challenge——至少 1 条发现被审查）
Stage 4   — 同行评审        （置信度评分、偏见检测、遗漏视角）
```

> ⚠️ **Stage 3.5 是真正的闸门。** 没有 challenge 调用就不会推进。不再自动盖章"已验证"。

---

## 🚀 本地部署

### 方案 A：裸机（Python venv）

```bash
git clone https://github.com/inoribea/DeDoldrums.git && cd DeDoldrums
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                      # 总共 4 个依赖
cp .env.example .env                                 # 配置 LLM 角色
```

**CLI 模式：**

```bash
python main.py "量子计算对 RSA 的真实威胁时间线是什么？"
python main.py --goal --budget 30 "比较可行的 AGI 治理框架"
```

**Web UI 模式：**

```bash
python bridge.py                     # → http://127.0.0.1:18765
```

浏览器打开即可使用。输入问题，实时观看 5.5 阶段管线推进，思考过程可折叠展开。

### 方案 B：Docker

```bash
git clone https://github.com/inoribea/DeDoldrums.git && cd DeDoldrums
cp .env.example .env
docker compose up -d                 # → http://localhost:18765
```

`docker-compose.yml` 将 `./memory/` 挂载为卷——知识在重启后持续保留。

### 方案 C：systemd（Linux 服务器）

```bash
sudo cp systemd/research-agent.service /etc/systemd/system/
sudo useradd -r -s /bin/false research
sudo mkdir -p /opt/research-agent && sudo cp -r . /opt/research-agent/
sudo cp .env /opt/research-agent/
cd /opt/research-agent && python -m venv .venv && .venv/bin/pip install -r requirements.txt
sudo systemctl daemon-reload && sudo systemctl enable --now research-agent
```

### LLM 配置

每个研究角色可独立使用不同模型/提供商。格式：`提供商/模型ID`。

```bash
LLM_TOOL_CALLING=openai/gpt-5.5              # 核心循环，工具选择和管线调度
LLM_CREATIVE=anthropic/claude-sonnet-5       # 发散思维，视角发现与透镜反思
LLM_CONVERSATIONAL=openai/gpt-5.5-mini       # 用户交互，问题精炼与最终简报
LLM_CONTENT_REVIEW=openai/gpt-5.5            # 对抗闸门，挑战与验证

# 各提供商 API key
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
KIMI_API_KEY=sk-...
```

### Vercel 前端部署

```bash
cd vercel && npm install
# 在 Vercel 控制台设置 BRIDGE_URL + BRIDGE_API_KEY
npx vercel deploy --prod
```

前端每 2 秒通过 Vercel API 路由轮询 bridge——无需直连。

---

## 🏗️ 架构

```
research_agent/
├── agent_loop.py       # 异步主循环（LLM 决策 → 工具调度 → 阶段推进）
├── handler.py          # 工具路由 + 5.5 阶段状态机
├── tools.py            # explore / reflect / challenge / crystallize
├── llm.py              # 5 种后端 + 7 提供商注册表 + 角色路由器
├── memory.py           # L0-L4 分层记忆
├── lenses.py           # 动态视角发现 + 9 透镜静态库
├── prompts.py          # STORM 各阶段 prompt 模板
├── goal_mode.py        # 持续自驱循环（移植自 GA）
├── main.py             # CLI 入口
├── config.py           # 基于角色的 LLM 配置 + 提供商解析
├── bridge.py           # aiohttp HTTP+SSE 服务器 + 内置前端托管
├── launch.py           # 一键启动 bridge + bot
├── adapters/           # Telegram / Discord bot 适配层
├── vercel/             # Next.js 14 + shadcn/ui 前端 + API 代理路由
├── Dockerfile          # 容器化部署
├── docker-compose.yml  # 一键 Docker 部署
└── systemd/            # systemd 服务模板
```

### 4 个知识工具

| 工具 | 参数 | 功能 |
|:---|:---|:---|
| `explore` | `query` + `source`（web/memory/url） | DuckDuckGo 搜索、记忆检索、URL 深度阅读 |
| `reflect` | `lens` + `focus` | 切换思维透镜（动态或静态）深度分析 |
| `challenge` | `target` + `mode` | 对抗压力测试：逻辑漏洞、隐藏假设、缺失证据、替代解释 |
| `crystallize` | `insight` + `category` | 将突破性洞察固化到分层记忆，供未来复用 |

---

## 📚 方法论

DeDoldrums 融合了四方工作：

| 来源 | 取什么 | 参考 |
|:---|:---|:---|
| **GenericAgent** | 执行框架（StepOutcome/dispatch/Goal Mode） | [lsdefine/GenericAgent](https://github.com/lsdefine/GenericAgent) |
| **STORM（原始论文）** | 动态视角发现 | [Shao et al., NAACL 2024](https://arxiv.org/abs/2402.14207) |
| **STORM（社区衍生版）** | 4 阶段框架 + 矛盾映射 + 同行评审 | [storm-research-method](https://github.com/kamilwpaczce-svg/storm-research-method) |
| **Caesar** | Generator-Verifier 对抗循环 | Liang et al., 2026 |

> 原始 STORM 论文输出 Wikipedia 风格文章；社区衍生版增添了矛盾映射和同行评审机制。本项目加入了强制对抗闸门和可作为一等公民使用的动态视角。

---

## 🙏 致谢

站在 [**GenericAgent**](https://github.com/lsdefine/GenericAgent) 的肩膀上——`StepOutcome`-dispatch 模式、Goal Mode 自驱循环、分层记忆设计均直接移植自 GA。

感谢 [**STORM 论文**](https://arxiv.org/abs/2402.14207)（Shao et al., NAACL 2024）提出的多视角分析，以及社区衍生版发明的矛盾映射与同行评审机制。

感谢 **Caesar**（Liang et al., 2026）的 Generator-Verifier 对抗验证框架。

---

## 📄 许可

[MIT](LICENSE)
