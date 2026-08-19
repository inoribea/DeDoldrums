# DeDoldrums 改造指南 v1

> 目的：把「硬门 + 漏桶」改造成「硬门 + 不漏桶」。
> 现状优势（**保留不动**）：机制级 adversarial gate、challenge 的 skeleton/grounding 双模式、角色级模型路由、L0-L4 记忆、动态透镜、矛盾地图。
> 核心问题（本指南要修的）：子代理回传无压缩契约（上下文被灌满，`compose_final_brief` 的 last-8 compaction 是在给这个漏买单）、无文档级审计、无盲点声明 artifact、无 human checkpoint、findings 落库不带来源定位。
> 改造人：专业开发者（不熟悉本项目上下文者亦可执行）。

---

## 改造优先级总览

| # | 改动 | 主要文件 | 工作量 | 风险 | 验收一句话 |
|---|---|---|---|---|---|
| P5 | findings 落库强制 schema | handler.py / prompts.py | 0.5 天 | 低 | 每条 finding 必带 source_url + confidence |
| P1 | sub_research 压缩契约 | tools.py / handler.py | 1 天 | 中 | 子代理回传 ≤10 条 (claim, source, confidence) 三元组 |
| P3 | 盲点声明强制 | prompts.py（STAGE3_SYNTHESIS） | 0.5 天 | 低 | 每份 brief 都有非空 Blind Spots 节 |
| P6 | 先落盘再压缩 | handler.py / compose_final_brief | 0.5 天 | 低 | 阶段产物在上下文截断前已写盘 |
| P2 | 文档级审计 document_audit | tools.py / handler.py / prompts.py | 1 天 | 中 | 预注册 rubric 五条，pass/fail + 缺口 ≤5 |
| P4 | human checkpoint（可配置） | handler.py / bridge.py | 0.5 天 | 低 | gate 后、brief 前可选暂停等人确认 |
| P7 | README 与布局对齐 | README.md | 顺手 | 零 | 文档路径与实际一致 |
| P8 | gate 凭证显式化 | handler.py | 0.5 天 | 低 | 无 audit pass 或降级记录不得出 brief |

**总工期 ≈ 4 个工作日。落地顺序按 P5 → P1 → P3/P6 → P2 → P4 → P7/P8。**

---

## P5 · findings 落库强制 schema（先做，一切的前提）

**问题**：`ResearchHandler.findings` 目前是无结构 list，grounding 只能事后补。

**改法**：
1. 定义 finding 结构：`{claim: str, source_url: str, confidence: enum[已知/推断/猜测], lens: str}`；
2. Stage 1 的 prompt（`prompts.py` 的 `STAGE1_MULTI_PERSPECTIVE`）要求子代理/主代理按此结构产出；
3. 进入 `self.findings.append(...)` 前做 schema 校验，缺 source_url 的 claim 降级为 confidence=猜测 并记录告警。

**验收**：单测断言——无 source_url 的 finding 要么被拒要么自动降级；`grounding` 从「补课」变「查账」。

---

## P1 · sub_research 压缩契约（最高优先，先于一切功能增强）

**问题**：`tools.py` 中 `sub_research` 工具的 schema 只有 `tasks: [{lens, question}]`，**回传结构未约束**——子代理分析结果直接汇总回流主上下文。你的 `compose_final_brief` 的 last-8 compaction 正是在给这个漏买单；修复后该 workaround 可逐步简化。

**改法**：
1. 给 `sub_research` 的**输出**加 JSON schema 强制：
   ```json
   {
     "results": [{
       "claim": "string（一句话，可验证）",
       "source_url": "string（可定位）",
       "confidence": "已知|推断|猜测",
       "lens": "string"
     }],
     "maxItems": 10
   }
   ```
2. 每个子代理的指令加蒸馏约束：「只回传三元组；原始搜索过程、失败查询、长篇引用一律不回传」；
3. 主上下文只接收三元组，不接收子代理的原始输出。

**验收**：集成测试断言 sub_research 回传结构合法且 ≤10 条；长会话上下文增长斜率明显下降（可用 token 计量对比改造前后）；last-8 compaction 触发频率下降。

---

## P3 · 盲点声明强制（低成本高价值）

**问题**：brief 无强制盲点字段，「覆盖不足装已知」。

**改法**：`STAGE3_SYNTHESIS` prompt 模板强制 brief 含 `## Blind Spots` 节（搜过什么/查过什么源/没试什么框架）；覆盖不足显式标 `[可能不全]`。矛盾地图里已有「collective blind spots」维度，把它提升为 brief 的强制节。

**验收**：每份产出 brief 的 Blind Spots 节非空且具体（非「需要更多研究」类空话）。

---

## P6 · 先落盘再压缩

**问题**：`compose_final_brief` 用「sys + question + last 8 outputs」压缩上下文，但压缩前阶段产物（矛盾地图、synthesis）是否在盘上不保证（`crystallize` 是手动的）。

**改法**：
1. 每个 stage 边界自动写盘：矛盾地图、synthesis 各存一份到 memory 会话归档（如 `memory/L4_archive/<session>/`）；
2. 压缩/截断上下文**之前**，确保这些产物已落盘；
3. 崩溃/中断后可从盘上恢复，无需重跑已完成的 stage。

**验收**：模拟长会话中断，能从盘上恢复矛盾地图与 synthesis 全文。

---

## P2 · 文档级审计 document_audit（gate 的补强，不是复活 peer review）

**问题**：`challenge` 是**发现级**（对抗单个 finding，带 skeleton/grounding——很好），但没有**文档级**体检：每个 lens 是否有产出？盲点声明诚实吗？全部 findings 来源可定位吗？标签正确吗？

**改法**：
1. 新增 `document_audit` 工具（或扩展 `challenge` 的 `all` 模式为文档级），预注册 rubric 五条：
   | # | 判据 | 检查方式 |
   |---|---|---|
   | 1 | 每条关键论断有可定位来源 | 抽查 ≥5 条 findings 的 source_url |
   | 2 | 反例被考虑 | counterevidence 是否非空且具体 |
   | 3 | 盲点声明诚实 | Blind Spots 是否列出搜过/没试，非空话 |
   | 4 | 标签正确 | [已知] 都有来源；无来源的标了猜测 |
   | 5 | 覆盖完整 | 每个 lens 都有产出，无空转方向 |
2. audit 在 gate 前跑，输出 pass/fail + 缺口清单（≤5 条）；
3. 与 challenge 的关系：challenge 打单点，audit 查整体，两者互补。

**验收**：audit 对「逻辑对但覆盖缺」的文档能报 FAIL（challenge 单独过不了这条）。

---

## P4 · human checkpoint（可配置，默认开）

**问题**：gate 通过 → 直接 final brief，人全程只看结果。

**改法**：
1. gate 通过后、final brief 生成前，加可选 pause（默认开）；
2. 暂停时展示矛盾地图 + synthesis 摘要 + audit 缺口，等人类确认或改向；
3. `--no-human-gate` 关闭，行为与现在一致；
4. **注意**：这是人闸，不是再一轮 LLM review——不要复活已删除的 Stage 4 peer review（那轮删除是正确决策，成本大于收益）。

**验收**：默认时流程卡在检查点等人；`--no-human-gate` 时无感知。

---

## P7 · README 与布局对齐

**问题**：README 架构图画的是 `research_agent/` 子目录，实际代码在根目录（tools.py/handler.py/... 都在根）。你自己先犯了「双源漂移」。

**改法**：二选一——改 README 架构图为实际布局，或把代码挪进 `research_agent/`（后者动静大，推荐前者）。

---

## P8 · gate 凭证显式化

**问题**：hard gate 现在靠「challenge 工具被调用过」判定，但 audit 未纳入 gate 条件。

**改法**：状态机 `advance` 到 final brief 前，必须满足：audit pass **或** 显式降级记录（降级理由入 open_questions）。无两者不得出 brief。

---

## 测试与回归策略

- 现有 tests/ 已覆盖状态机与 bridge（110 commits 的积累）——每项 P 配单测 + 集成测试；
- 重点回归：stage 状态机（刚删过 Stage 4，别让新状态破坏流转）、bridge 流式输出、last-8 compaction 行为变化（P1 生效后它应少触发，不要依赖它兜底）；
- 新增测试锚点：`tests/` 下按 P 编号建用例文件（如 `test_compression_contract.py`）。

---

## 验收总清单

- [ ] P5：findings 全带 source_url + confidence，无来源自动降级
- [ ] P1：sub_research 回传 ≤10 三元组，主上下文只收三元组
- [ ] P3：brief 强制 Blind Spots 节，非空话
- [ ] P6：阶段产物先落盘后压缩，中断可恢复
- [ ] P2：document_audit 五条 rubric，能抓「逻辑对但覆盖缺」
- [ ] P4：human checkpoint 默认开、可关，不复活 peer review
- [ ] P7：README 与实际布局一致
- [ ] P8：无 audit pass/降级记录不得出 brief
- [ ] 全量测试通过，last-8 compaction 触发频率下降（可选量化）

---

## 设计原则备忘（改造时对照）

1. **门要硬，桶不能漏**：机制级强制（gate/audit）值得，上下文纪律（压缩契约/落盘）同样值得——别修了门忘了桶；
2. **可验证 > 自报**：audit 的判据全部可外部检查，不让模型自评「我查过了」；
3. **人闸 ≠ LLM review**：人看矛盾地图改向，LLM 已经干完活；
4. **单源不漂移**：README 与代码、config 与代码，只允许一处为真。
