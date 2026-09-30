"""Evidence-grounded draft artifacts for Research Operator."""

from __future__ import annotations

from app.tools.document_tool import DocumentTool


class DocumentGenerator:
    name = "document_generator"
    description = "Creates reviewable Markdown and DOCX drafts only from retrieved evidence references."

    _titles = {
        "literature_review": "Literature Review Draft",
        "research_proposal": "Research Proposal Draft",
        "experiment_plan": "Experiment Plan Draft",
        "technical_report": "Technical Report Draft",
        "customer_delivery_report": "Customer Delivery Report Draft",
        "project_report": "Research Project Report Draft",
        "meeting_summary": "Meeting Summary Draft",
        "technical_documentation": "Technical Documentation Draft",
    }

    def __init__(self, document_tool: DocumentTool | None = None) -> None:
        self._document_tool = document_tool or DocumentTool()

    def generate(self, task_id: str, *, document_type: str, objective: str, evidence_refs: list[dict[str, object]]) -> dict[str, object]:
        if not evidence_refs:
            return {"status": "INSUFFICIENT_EVIDENCE", "message": "当前没有可验证资料，不能生成包含科研结论的文档。", "artifacts": []}
        title = self._titles.get(document_type, "Research Draft")
        source_lines = []
        for index, evidence in enumerate(evidence_refs, start=1):
            label = evidence.get("paper_title") or evidence.get("source") or "未命名资料"
            section = evidence.get("section") or "未标注章节"
            source_lines.append(f"{index}. {label} · {section}")
        content = self._structured_content(document_type, objective, source_lines)
        markdown = self._document_tool.generate_markdown(task_id, title, content)
        docx = self._document_tool.generate_docx(task_id, title, content)
        return {"status": "draft_ready", "title": title, "evidence_count": len(evidence_refs), "artifacts": [markdown, docx], "human_review_required": True, "boundary": "AI 辅助生成草稿，需人工审核后方可作为正式交付物。"}

    @staticmethod
    def _structured_content(document_type: str, objective: str, source_lines: list[str]) -> str:
        """Use fixed review templates; never turn source labels into claims."""
        common = ["## Task objective", objective, "\n## Evidence references", *source_lines]
        templates = {
            "literature_review": [
                ("Introduction", "根据上述 Evidence 整理研究背景，待人工核对适用范围。"),
                ("Research Progress", "按来源资料梳理已有研究进展，不补充未出现的实验结论。"),
                ("Method Comparison", "仅比较 Evidence 引用所能支持的方法信息与条件差异。"),
                ("Challenges", "记录当前 Evidence 不能覆盖或需要人工复核的限制。"),
                ("Future Direction", "形成待验证方向，不作为已证实的科研结论。"),
            ],
            "research_proposal": [
                ("Background", "基于已引用 Evidence 描述项目背景。"),
                ("Research Problem", "明确需要继续验证的问题与资料边界。"),
                ("Innovation Opportunity", "仅提出待人工确认的机会，不宣称创新已被证明。"),
                ("Technical Route", "将可验证资料转为供负责人审核的技术路线草案。"),
                ("Experiment Plan", "列出需要后续由研究人员确认的验证计划。"),
            ],
            "experiment_plan": [
                ("Research Question", "记录需验证的问题及现有资料范围。"),
                ("Evidence Context", "关联可追溯 Evidence，不复制论文全文。"),
                ("Validation Design", "提供待人工审核的实验设计框架。"),
                ("Risk and Boundary", "说明条件、样本或证据不足需补充的位置。"),
            ],
            "project_report": [
                ("Requirement", "整理当前任务目标与需求边界。"),
                ("Solution", "形成基于 Evidence 的待审核解决方案草案。"),
                ("Implementation", "列出需负责人确认的受控实施步骤。"),
                ("Validation", "明确后续验证和人工审核要求。"),
            ],
            "meeting_summary": [
                ("Meeting context", "整理当前已引用 Evidence 与待确认讨论范围。"),
                ("Decision candidates", "仅记录需人工确认的判断，不形成自动决策。"),
                ("Action items", "列出需负责人分配和确认的后续事项。"),
            ],
            "technical_documentation": [
                ("Technical scope", "说明当前 Evidence 所覆盖的技术范围与边界。"),
                ("Evidence references", "保留来源引用，不补充未验证的技术结论。"),
                ("Validation notes", "列出需要进一步复核的条件与限制。"),
            ],
        }
        sections = templates.get(document_type, [
            ("Evidence-grounded draft scope", "本草稿仅整理当前 Evidence；不生成无依据科研结论。"),
            ("Recommended validation", "请核对来源研究对象、条件与适用范围后再形成正式结论。"),
        ])
        content = list(common)
        for heading, guidance in sections:
            content.extend([f"\n## {heading}", guidance])
        content.extend(["\n## Human review", "AI 辅助生成，需人工审核确认后方可作为正式交付物。"])
        return "\n".join(content)
