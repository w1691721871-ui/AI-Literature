# API 概览

## 原有单篇 Agent

- `POST /agent/analyze-paper`：上传并分析一篇 PDF。
- `POST /agent/papers/{paper_id}/questions`：对当前论文连续追问。

## 科研空间

- `POST /research/papers/upload`：上传论文、解析、切片、Embedding 并建立索引。
- `GET /research/papers`：获取论文元数据；不返回全文。
- `GET /research/papers/{paper_id}`：查看论文安全元数据。
- `DELETE /research/papers/{paper_id}`：删除论文、切片、关联记录和索引映射。
- `POST /research/papers/{paper_id}/analyze`：从论文库进入既有单篇 Agent。

## 多论文 RAG

- `POST /research/questions`：请求体为 `{ "question": "...", "paper_ids": [] }`。返回回答、引用、任务计划、`agent_trace` 和 `retrieval_evaluation`。
- `POST /research/generate-report`：请求体为 `{ "report_type": "literature_review", "paper_ids": [] }`。支持 `literature_review`、`technology_roadmap`、`research_gap`。
- `GET /research/questions/history`：获取历史问答。
- `GET /research/questions/history/{record_id}`：恢复一条问答与引用。

论文的 `analysis_status` 保持旧接口兼容；`quality_status` 表示知识库准备阶段：`parsed`、`indexed`、`ready` 或 `failed`。只有 `ready`/`indexed` 论文可用于多论文检索。
