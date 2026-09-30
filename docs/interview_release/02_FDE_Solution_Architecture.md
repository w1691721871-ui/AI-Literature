# FDE Solution Architecture

## 从客户需求到可验收交付

ResearchOS 的 FDE 方案不从“部署一个模型”开始，而从客户资料、目标与验收边界开始。

```text
客户需求
  ↓
需求调研与资料授权范围
  ↓
Solution Blueprint
  ↓
Research Workspace + 知识空间 + Human Review
  ↓
受控 Agent 工作流与 Evidence 复核
  ↓
Research Brief / Customer Delivery Report
  ↓
客户确认与后续优化
```

## 1. 客户需求

| 场景 | 典型问题 | 需确认的信息 |
| --- | --- | --- |
| 高校实验室科研管理 | 资料增长、交接成本高、方向难沉淀 | 资料授权、团队角色、研究目标 |
| 企业研发部门技术调研 | 技术资料分散、调研结论难追溯 | 业务问题、技术范围、验收口径 |
| 横向科研项目申报 | 供需映射和成果规划断层 | 企业需求、研究能力、交付责任人 |

## 2. 方案设计

- **Research Workspace**：承载研究目标、策略、任务、Evidence 摘要、Review 与交付草案。
- **Knowledge Space**：仅管理已授权、已解析并完成索引的资料。
- **Finite Research Loop**：策略规划后对每个子任务独立检索、验证 Evidence、检测条件差异，并在预算内决定继续、重规划或停止。
- **Human Review**：Reviewer / Leader 明确审核，不由 AI 自动批准判断或创建正式 Action。

## 3. 技术架构映射

| 客户问题 | ResearchOS 模块 | 交付边界 |
| --- | --- | --- |
| 资料分散 | Paper Library / Knowledge Space / RAG | 仅处理授权上传资料 |
| 结论难追溯 | Evidence Validation / Evidence Graph | 章节级引用提示，不等同于精确页码溯源 |
| 条件差异难解释 | Claim Extraction / Conflict Detection | 提示 potential conflict 或 context difference，不裁决科研真伪 |
| 协作审核不足 | Workspace Workflow / Review Center | 角色为产品模型；当前不含真实账号体系 |
| 交付材料分散 | Research Brief / Customer Delivery Report | AI 辅助草案，需负责人或客户确认 |

## 4. 交付流程

1. 需求调研：确认目标、资料边界、角色和验收标准。
2. 环境配置：创建 Workspace，导入授权资料，检查解析和索引状态。
3. 受控验证：执行真实研究任务，检查 Evidence、冲突提示和人工审核流程。
4. 交付沟通：生成 Research Brief、Solution Blueprint 与 Customer Delivery Report。
5. 客户确认：记录资料不足、待确认问题和下一阶段优化范围。

## 5. 验证结果的表达方式

可验证的内容包括：接口可用性、资料数量、索引状态、Evidence 是否可追溯、Review 是否经人工触发。不得把这些结果描述为“科研结论正确”“客户价值已实现”或“效率提升百分比”。
