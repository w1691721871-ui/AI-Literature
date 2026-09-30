# 5 分钟 FDE 面试演示脚本

## 演示前准备

- 启动 FastAPI 与前端静态服务。
- 打开 ResearchOS 首页，进入 **Solution Delivery**。
- 说明：客户场景为 Demo 模板；当前资料、Evidence 数与审核状态来自本地真实运行状态。不要把模板文案描述成真实客户案例。

## 0:00–0:30｜客户需求

**讲述：**“假设企业研发部门提出需求：希望分析 RAG 技术发展方向，同时希望团队能复核资料依据和不同研究条件下的差异。”

打开客户场景 **企业研发部门技术调研**，指出痛点是资料分散、调研难追溯、合作准备成本高。

## 0:30–1:00｜创建或选择 Workspace

进入 **Research Workspace**。说明 Workspace 保存研究目标、策略、已执行子任务、Evidence 摘要、Review 状态和交付草案。

**边界说明：**演示不自动创建客户 Workspace；真实实施时由客户授权资料和负责人确认后创建。

## 1:00–1:45｜AI 制定 Research Strategy

进入 **Research Command**。说明 Research Master 不是一次性摘要，而是：

```text
目标理解 → Strategy Planner → 子任务 → 独立检索 → Evidence → 决策
```

展示策略和 Agent Trace。强调 Trace 仅记录用户可理解的执行摘要，不展示 Prompt、Token 或思维链。

## 1:45–2:45｜Evidence 检索

进入 **Knowledge Space** 或 **Evidence**。说明资料完成解析、切分、向量化和索引后，RAG 通过 Query Rewrite、Hybrid Retrieval 与 Rerank 获取候选片段。

强调：系统只使用已授权、已索引资料；资料不足时后端应阻止无依据结论。

## 2:45–3:30｜条件差异 / 冲突提示

说明 Claim Extraction 在句级识别“对象、指标、方向、条件”；Conflict Detection 的目的不是裁决论文真假，而是识别：

- `potential_conflict`
- `context_difference`

演示时使用“可能存在条件差异，需要人工核验”的表达，不声称已完成某个真实科研冲突的最终裁决。

## 3:30–4:15｜Reviewer 审核

返回 **Research Workspace → Review Center**。说明：

- Researcher 可以上传资料和发起任务。
- Reviewer / Leader 才可审核 Evidence 关联判断。
- AI 不会自动批准，也不会自动创建正式 Action。

## 4:15–5:00｜Research Brief 与客户交付

回到 **Solution Delivery**，展示：

- 真实 Admin Overview（Workspace、任务、知识片段、待审核项）
- Potential Value Indicators（不承诺百分比收益）
- Customer Delivery Report（AI 辅助生成、需客户确认）

**收束话术：**“ResearchOS 的重点不是让模型多说一段答案，而是让研究资料、依据、人工审核和交付草案进入同一条可追溯的科研协作路径。”

## 常见现场风险与处理

- **无资料或索引为空**：展示 `NEEDS_REAL_DATA` / 资料不足状态，说明这是可信边界，不用 Demo 数据冒充真实资料。
- **模型服务不可用**：展示 System 与诊断状态，转为讲解已实现的受控工作流与测试边界。
- **Evidence 不足**：明确停止结论，说明下一步是补充授权资料或人工核验。
