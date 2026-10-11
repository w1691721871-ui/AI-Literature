# Technical Architecture

## 产品技术栈

| 层级 | 当前实现 |
| --- | --- |
| Frontend | Vue 3 CDN、JavaScript、CSS、Service Worker |
| Backend | FastAPI、Python、REST API |
| LLM | Qwen / DashScope |
| Knowledge | SQLite、PDF 解析、Chunking、Embedding、FAISS |
| Retrieval | Query Rewrite、Hybrid Retrieval、Rerank |
| Trust | Evidence Validation、Claim Extraction、Conflict Detection、Human Review |
| Agent | Research Master、Research Strategy Planner、Finite Research Loop、Research Worker |

## 核心研究链路

```text
Authorized PDF
  → PDF Parse
  → Chunking
  → Embedding
  → FAISS Index
  → Query Rewrite
  → Hybrid Retrieval + Rerank
  → Evidence Validation
  → Claim Extraction
  → Conflict Detection
  → Human Review / Research Brief
```

## Agent 层

### Research Strategy Planner

按 comparison、summary、gap_analysis、direction_discovery 等任务类型生成用户可理解的结构化策略和子任务，不保存内部推理链。

### Finite Research Loop

每个子任务独立完成检索、Evidence 验证、冲突检测和中间评估；Evidence 是否充分会真实影响下一步子任务、重规划或停止。循环具备子任务、检索轮次、步骤和模型调用预算，避免无限检索。

### Evidence 与 Human Review

- Evidence 使用已有 `paper_id + chunk_id` 等稳定引用。
- Claim Extraction 使用确定性句级规则，不通过 LLM 伪造 Claim。
- Conflict Detection 只提示潜在冲突或条件差异，不判断哪篇论文“正确”。
- Reviewer / Leader 审核后才可以进入后续交付草案状态。

## P5 Solution Delivery Layer

P5 不修改 RAG 或 Agent 核心，而是增加只读的方案展示服务：

- Customer Scenario Template
- Solution Blueprint
- Potential Value Indicators
- Admin Overview
- Demo Flow
- Customer Delivery Report

所有 P5 数据来自固定演示模板或当前 SQLite 中的真实计数；不创建客户数据，不承诺 ROI。
