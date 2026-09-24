# AI Research Agent 架构

系统有两条独立链路：`PaperAnalysisAgent` 保留单篇论文分析与连续追问；`ResearchAgent` 专注于多论文检索问答和研究报告。两者共用论文库，但不相互替代。

```text
PDF → pdf_service → papers
                 ↓
       chunking_service → embedding_service → paper_chunks → FAISS
                                                            ↓
问题 → ResearchPlanner → Query Rewrite → Retrieval → Rerank → Qwen-plus
                                                            ↓
                    rag_query_records / agent_traces / 前端引用与质量卡片
```

SQLite 保存论文元数据、提取文本、切片、历史报告、RAG 问答和用户可见的 Agent 执行摘要。上传与删除论文后会整体重建本地 FAISS 索引，保证小规模知识库映射一致。

`agent_traces` 只保存用户可理解的操作里程碑，例如“检索相关论文”，不保存提示词、Authorization 头、API Key 或模型内部思维链。
