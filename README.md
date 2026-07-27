# ResearchAgent

> 基于 [GenericAgent](https://github.com/lsdefine/GenericAgent) 哲学 + 混合 [STORM](https://arxiv.org/abs/2402.14207) 多视角研究法的自我进化研究 Agent。

ResearchAgent 将 STORM 的多视角研究管线嵌入 GenericAgent 的执行框架——极简种子（~1,700 行）、4 个知识操作工具、5.5 阶段自动推进、分层记忆自我进化。你只需要提问，Agent 自主发现视角、检索信息、反思分析、对抗验证、合成报告。

---

## 特性

```
Stage 0   — 动态视角发现（基于检索结果生成该主题独有的分析视角）
Stage 1   — 多视角扫描（动态视角 + 9 透镜库兜底，独立探索）
Stage 2   — 矛盾映射（找出视角冲突、共识和盲点）
Stage 3   — 综合合成（跨视角连接 + 结构化报告）
Stage 3.5 — 对抗验证闸门（Generator-Verifier 自动压力测试每个关键发现）
Stage 4   — 同行评审（置信度评分 + 偏见检测 + 缺失视角）
```

- **极简核心**：4 个工具（`explore` / `reflect` / `challenge` / `crystallize`）覆盖完整研究闭环
- **动态视角**：不预设固定角色，从主题自身特征推导分析维度（取自原始 STORM 论文）
- **对抗验证**：每个关键发现自动经过 Generator-Verifier 压力测试（取自 Caesar）
- **自我进化**：固化突破性洞察为可复用思维 SOP → Goal Mode 持续深挖直到预算耗尽
- **分层记忆**：L0 元规则 → L1 模式索引 → L2 领域知识 + 图拓扑 → L3 思维 SOP → L4 会话归档
- **多平台接入**：Bridge + SSE → Telegram / Discord / Vercel Web 通过薄适配层接入

---

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/inoribea/ResearchAgent.git
cd ResearchAgent

# 2. 安装最小依赖（4 个包）
pip install -r requirements.txt

# 3. 配置 LLM API key
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY

# 4. 单次研究
python main.py "WebAssembly 对前端框架生态的长期影响是什么？"

# 5. Goal Mode — 30 分钟持续深挖
python main.py --goal --budget 30 "量子计算对密码学的真实威胁时间线"
```

### Bridge 模式（多平台接入）

```bash
# 启动研究后端
python bridge.py    # 监听 http://127.0.0.1:14168

# 可选：启动 bot
python adapters/telegram_bot.py
python adapters/discord_bot.py
```

### Vercel 前端部署

```bash
cd adapters/vercel
npm install
# 在 Vercel 设置环境变量: BRIDGE_URL, BRIDGE_API_KEY
npx vercel deploy --prod
```

---

## 架构

```
research_agent/
├── agent_loop.py       # 异步主循环（LLM 决策 → 工具调度 → 阶段推进）
├── handler.py          # 工具路由 + 5.5 阶段状态机（-1→0→1→2→3→3.5→4）
├── tools.py            # 4 个知识工具：explore / reflect / challenge / crystallize
├── llm.py              # OpenAI 兼容 LLM 客户端（httpx，无框架依赖）
├── memory.py           # L0-L4 分层记忆 + L2 图结构索引
├── lenses.py           # 动态视角发现 + 9 透镜库兜底
├── prompts.py          # STORM 各阶段 prompt 模板
├── goal_mode.py        # 持续自驱循环（移植自 GA reflect/goal_mode.py）
├── main.py             # CLI 入口
├── config.py           # 环境变量配置
├── bridge.py           # aiohttp HTTP+SSE Bridge
├── launch.py           # 一键启动 bridge + bot
├── adapters/           # Telegram / Discord / Vercel 适配层
├── memory/             # 记忆存储目录（L0 规则 / L1 索引 / L2 知识 / L3 SOP / L4 归档）
└── requirements.txt    # openai, httpx, beautifulsoup4, aiohttp
```

### 4 个知识工具

| 工具 | 作用 | STORM 对应 |
|------|------|-----------|
| `explore` | 多层检索：Web 搜索 / 记忆库 / URL 深度阅读 | 信息收集 |
| `reflect` | 切换透镜审视发现 | 多视角分析 |
| `challenge` | 对抗压力测试（逻辑漏洞 / 隐藏假设 / 缺失证据 / 替代解释） | 矛盾验证 |
| `crystallize` | 固化洞察到记忆（领域知识 / 思维模式 / 透镜组合 / 雷区） | 自我进化 |

---

## 方法论来源

ResearchAgent 采用**混合路线**，融合了三方方法论：

| 来源 | 贡献 | 说明 |
|------|------|------|
| **GenericAgent** | 执行框架 | 极简种子 + StepOutcome-dispatch 模式 + Goal Mode 自驱循环 |
| **原始 STORM 论文** | 动态视角发现 | Shao et al., *NAACL 2024*. [arXiv:2402.14207](https://arxiv.org/abs/2402.14207) |
| **STORM 社区衍生版** | 4 阶段框架 | [kamilwpaczce-svg/storm-research-method](https://github.com/kamilwpaczce-svg/storm-research-method) — 矛盾映射 + 同行评审 |
| **Caesar** | 对抗验证 + 图搜索 | Liang et al., 2026. Generator-Verifier 闸门 + 发现间拓扑关系 |

> 原始 STORM 论文输出 Wikipedia 风格文章；社区衍生版发明了原始论文没有的矛盾映射/同行评审/置信度评分机制，输出决策者导向的研究简报。本项目的混合路线在社区版基础上进一步升级——视角发现改为动态（取原始 STORM 之长），新增 Stage 3.5 对抗验证闸门（取 Caesar 之长），记忆层增加图结构索引。

### 与 GenericAgent 的对比

| 维度 | GenericAgent | ResearchAgent |
|------|:--:|:--:|
| 核心循环 | Perceive→Reason→Execute→Memory | Question→Discover→Explore→Reflect→Challenge→Verify→Crystallize |
| 工具数 | 9（计算机控制） | 4（知识操作） |
| 研究阶段 | — | 5.5 阶段 |
| 视角来源 | — | 动态发现 + 透镜库兜底 |
| 对抗验证 | — | Stage 3.5 闸门 |
| 自我进化 | 任务路径→SOP | 研究路径→思维模式 |
| 记忆系统 | L1-L4（任务导向） | L0-L4 + L2 图索引（知识导向） |
| Goal Mode | 创造→检验→改进 | 探索→检验→深化 |
| 代码量 | ~3K 行（核心） | ~1.7K 行 |

---

## 致谢

本项目深受 [GenericAgent](https://github.com/lsdefine/GenericAgent) 的极简哲学和工程实践启发——3K 行代码覆盖完整计算机控制 Agent，证明了"极简种子 + 自我进化"的可行性。`agent_loop.py` 的 StepOutcome-dispatch 模式、Goal Mode 的自驱循环、分层记忆设计均直接移植自 GenericAgent。

感谢 [STORM 论文](https://arxiv.org/abs/2402.14207)（Shao et al., 2024）提出的动态视角发现和多视角分析的核心洞察，以及 STORM 社区衍生版发明了矛盾映射、同行评审、置信度评分等实用机制。

感谢 Caesar（Liang et al., 2026）的 Generator-Verifier 对抗验证框架，直接启发了 Stage 3.5 闸门设计和 L2 图结构索引。

---

## 许可

[MIT](LICENSE) — 与 GenericAgent 保持一致。

---

*设计哲学：极简种子 + 自我进化 + 动态多视角 + 对抗性验证。*
