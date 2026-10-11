# 简历项目版本

## ResearchOS｜AI 科研决策与执行平台（产品原型）

### 项目背景

面向高校实验室、企业研发团队和产学研协作场景，解决科研资料分散、研究结论缺少依据、协作审核与交付过程不连续的问题。

### 技术架构

Vue 3 CDN + FastAPI + Qwen / DashScope + SQLite + PDF 解析 + Chunking + Embedding + FAISS。检索侧包含 Query Rewrite、Hybrid Retrieval 与 Rerank；可信侧包含 Evidence Validation、句级 Claim Extraction、Conflict Detection 与 Human Review。

### 核心贡献

- 设计并实现 Evidence-driven Research Workspace：将研究目标、策略、子任务、Evidence、冲突提示、人工审核与交付草案组织为持续工作流。
- 构建 Finite Research Loop：子任务独立检索和 Evidence 评估，支持有限重规划、无新 Evidence 停止和人工审核状态，不暴露模型思维链。
- 完成 Research Workspace 团队协作产品模型：Researcher、Reviewer、Leader 角色，以及 Review Center、Evidence Graph Lite 和 Research Brief。
- 设计 P5 FDE Solution Delivery Layer：客户场景、Solution Blueprint、真实运行概览、Potential Value Indicators、Demo Flow 与 Customer Delivery Report。

### 项目成果

- 打通资料上传、解析、切分、向量索引、RAG 检索、Evidence 关联、条件差异提示、人工审核和研究交付草案的产品代码路径。
- 本地验收时，诊断接口显示 7 篇已入库资料、180 个知识片段和 180 个已保存向量片段；该数据仅说明本地运行状态。
- 通过单元测试验证策略规划、有限循环、Evidence/Conflict、Workspace 工作流与 P5 Solution Delivery 的 fixture 行为；不将 fixture 写入生产 SQLite 或 FAISS。

### 真实边界

项目为 AI Agent 产品原型，不声称真实客户部署、收入、科研准确率或效率提升。科研结论必须以已授权资料、Evidence 和人工审核为前提。
