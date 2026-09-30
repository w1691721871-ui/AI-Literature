"""Deterministic, user-readable planning for the Research Operator Workspace.

This planner deliberately does not call an LLM.  It turns a stated goal into
an auditable, bounded proposal that a researcher can inspect before any tool
is invoked.
"""

from __future__ import annotations


class ResearchComputerTaskPlanner:
    """Create a safe plan for one controlled Research Computer task."""

    _document_outputs = {
        "literature_review": "Evidence-linked literature review draft",
        "experiment_plan": "Evidence-linked experiment planning draft",
        "research_proposal": "Evidence-linked research proposal draft",
        "project_report": "Evidence-linked project report draft",
        "file_organization": "Approval-gated research file organization plan",
        "browser_research": "External-source candidate review request",
    }

    def preview(self, goal: str) -> dict[str, object]:
        normalized = goal.strip()
        if not normalized:
            raise ValueError("请输入需要由 Research Operator 处理的科研任务。")
        task_type = self.classify(normalized)
        plan = self.build_plan(normalized, task_type)
        return {
            "goal": normalized,
            "task_type": task_type,
            "task_label": self._label(task_type),
            "expected_output": self._document_outputs[task_type],
            "resource_boundary": "仅使用现有知识库、授权工作区文件或待人工核验的外部候选来源；不会自动修改原始资料。",
            "risk_summary": "所有写入、导入、下载和正式交付均需人工批准；无 Evidence 时不形成科研结论。",
            "plan": plan,
        }

    @staticmethod
    def classify(goal: str) -> str:
        text = goal.lower()
        if any(word in text for word in ("整理", "目录", "分类", "文件")):
            return "file_organization"
        if any(word in text for word in ("网页", "browser", "外部来源", "最新论文", "最新")):
            return "browser_research"
        if any(word in text for word in ("实验", "验证", "experiment")):
            return "experiment_plan"
        if any(word in text for word in ("申报", "proposal", "横向项目", "合作方案")):
            return "research_proposal"
        if any(word in text for word in ("项目报告", "交付报告", "project report")):
            return "project_report"
        return "literature_review"

    def build_plan(self, goal: str, task_type: str) -> list[dict[str, object]]:
        steps = [self._step("understand", "理解研究目标", "task_understanding", "Research Operator", "明确任务边界、目标和预期交付物。", "LOW", False)]
        if task_type == "file_organization":
            steps.extend([
                self._step("scan_files", "扫描授权研究文件", "file_system", "File Tool", "识别可读取的资料类型与组织范围。", "LOW", False),
                self._step("organize", "生成资料组织方案", "literature_organization", "Literature Organization Skill", "只生成分类建议，不移动、复制或删除文件。", "HIGH", False),
            ])
        elif task_type == "browser_research":
            steps.extend([
                self._step("external_search", "检索外部来源候选", "browser_research", "Browser Agent", "外部来源只作为候选，必须人工核验后才能进入正式资料流程。", "MEDIUM", False),
                self._step("source_review", "准备来源核验清单", "research_management", "Research Management Skill", "记录来源候选与核验边界，不自动导入知识库。", "HIGH", False),
            ])
        else:
            steps.extend([
                self._step("retrieve", "检索既有科研 Evidence", "knowledge_retrieval", "Knowledge Tool", "仅使用可追溯的已有知识库 Evidence。", "LOW", True),
                self._step("read", "整理论文与研究要点", "paper_reading", "Paper Reading Skill", "按方法、实验、局限和未来方向整理证据范围。", "LOW", True),
                self._step("prepare", "准备研究交付草稿", "research_writing", "Research Writing Skill", "以 Evidence ID 绑定的草稿待人工审核。", "MEDIUM", True),
            ])
        steps.extend([
            self._step("approval", "等待人工批准", "research_management", "Research Management Skill", "人工确认后才会创建本地草稿或执行受控后续动作。", "MEDIUM", False),
            self._step("deliver", "记录可审核交付物", "delivery", "Research Operator", "保存交付物路径与 Evidence 引用，不自动发布。", "LOW", False),
        ])
        for index, step in enumerate(steps, start=1):
            step["step"] = index
            step["goal_summary"] = goal[:180]
        return steps

    @staticmethod
    def _step(task_id: str, task_name: str, skill: str, required_tool: str, reason: str, risk_level: str, evidence_requirement: bool) -> dict[str, object]:
        return {
            "id": task_id,
            "task_name": task_name,
            "action": task_name,
            "type": skill,
            "skill": skill,
            "required_tool": required_tool,
            "tool": required_tool,
            "reason": reason,
            "purpose": reason,
            "expected_output": "可审核执行摘要",
            "evidence_requirement": evidence_requirement,
            "risk_level": risk_level,
            "status": "pending",
        }

    @staticmethod
    def _label(task_type: str) -> str:
        return {
            "literature_review": "文献综述与研究比较",
            "experiment_plan": "实验验证规划",
            "research_proposal": "横向项目方案准备",
            "project_report": "项目交付报告准备",
            "file_organization": "科研资料组织",
            "browser_research": "外部来源候选调研",
        }[task_type]
