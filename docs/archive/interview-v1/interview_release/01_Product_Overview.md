# ResearchOS

## AI 科研决策与执行平台

### 用户痛点

高校实验室、企业研发部门与产学研团队常见的问题并不是“没有大模型”，而是资料、判断与交付之间缺少可靠链路：

- 论文、技术资料和项目材料分散，研究人员需要反复检索和人工整理。
- 研究讨论很难追溯到具体资料，团队成员无法快速判断结论的适用条件。
- 不同资料出现条件差异或方向不一致时，通用聊天工具往往直接给出单一答案，缺少人工复核入口。
- 从企业需求到研究方案、审核、项目与成果规划之间，缺少可展示的协作工作流。

### 目标客户

| 客户 | 典型任务 | ResearchOS 的作用 |
| --- | --- | --- |
| 高校实验室 | 文献管理、研究方向讨论、学生协作 | 建立可检索的知识空间与 Evidence 审核路径 |
| 企业研发部门 | 技术调研、合作方向准备 | 将需求、资料、依据和技术调研草案组织到同一工作流 |
| 产学研合作团队 | 横向项目申报、方案沟通、成果规划 | 提供可解释的方案蓝图、人工确认与交付材料 |

### 产品定位

ResearchOS 是面向科研组织的 **Evidence-driven Research Workspace** 产品原型。它不把 LLM 的一次回答当作科研事实，而是把研究目标、可检索资料、Evidence、冲突提示、人工审核和交付草案串成可复核路径。

```text
Research Goal
  → Research Strategy
  → Evidence Retrieval
  → Validation / Conflict Check
  → Human Review
  → Research Brief / Delivery Draft
```

### 核心价值

1. **资料资产化**：将已授权资料解析、切分并纳入可检索知识空间。
2. **研究过程可解释**：展示目标理解、策略、子任务、Evidence 与停止原因，不展示 Prompt 或模型思维链。
3. **可信边界清晰**：Evidence 不足时停止无依据结论；发现潜在冲突时保留条件差异并要求人工核验。
4. **团队协作可交付**：通过 Workspace、Reviewer/Leader 角色模型、Review Center、Evidence Graph 与 Research Brief 组织协作。
5. **FDE 可沟通**：通过客户场景、Solution Blueprint、Potential Value Indicators 与 Customer Delivery Report 展示从需求到验收的解决方案路径。

### 当前真实边界

ResearchOS 当前是本地产品原型：无真实登录、多租户隔离、实时协作通知或生产级审计；不宣称客户数量、收入、效率提升比例或科研准确率。P5 的 ROI 指标均是“可用于评估”的 Potential 指标，不是已验证收益。
