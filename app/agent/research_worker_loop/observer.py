"""Observe bounded tool results without inferring research facts."""


class ResearchWorkerObserver:
    def inspect(self, file_result: dict[str, object], data_result: dict[str, object] | None, knowledge_result: dict[str, object]) -> dict[str, object]:
        assets = int(file_result.get("asset_count", 0))
        sources = int(knowledge_result.get("source_count", 0))
        datasets = int((data_result or {}).get("dataset_count", 0))
        data_summaries = list((data_result or {}).get("summaries", []))
        has_usable_dataset = any(not item.get("error") and int(item.get("column_count", 0)) > 0 for item in data_summaries if isinstance(item, dict))
        needs_adjustment = datasets > 0 and not has_usable_dataset
        if needs_adjustment:
            summary = "发现数据文件，但未能确认可用字段；需先输出数据质量说明。"
        elif assets or sources:
            summary = f"发现 {assets} 个工作区文件和 {sources} 条可追溯知识库证据。"
        else:
            summary = "未发现可验证工作区文件或知识库证据。"
        return {
            "workspace_file_count": assets,
            "rag_evidence_count": sources,
            "dataset_count": datasets,
            "data_quality_ready": has_usable_dataset if datasets else None,
            "needs_adjustment": needs_adjustment,
            "summary": summary,
        }
