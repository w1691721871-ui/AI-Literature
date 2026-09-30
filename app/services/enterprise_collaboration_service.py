"""Organization collaboration services with explicit role checks.

This is a product-model permission layer rather than an identity provider.
Enterprise endpoints require an existing member id and validate its role
server-side; legacy single-user endpoints remain compatible.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.organization import (KnowledgeAccessGrant, Organization, OrganizationActivity,
                                     OrganizationMeeting, OrganizationMember, OrganizationProject)
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.research_document_revision import ResearchDocumentRevision
from app.models.research_task import ResearchTask
from app.services.database import SessionLocal, initialize_database


class PermissionDeniedError(Exception):
    """Raised when a member lacks an explicitly allowed action."""


class EnterpriseNotFoundError(Exception):
    """Raised for unavailable enterprise organization/project records."""


class EnterpriseCollaborationService:
    permissions = {
        "Researcher": {"create_task", "upload_material", "view_evidence", "create_project", "create_meeting"},
        "Reviewer": {"view_evidence", "review_evidence", "comment_draft", "create_meeting"},
        "Leader": {"view_project", "approve_deliverable", "view_quality", "create_project", "create_meeting"},
        "Admin": {"manage_members", "create_project", "view_project", "approve_deliverable", "view_quality", "upload_material", "view_evidence", "create_meeting"},
        # P22 enterprise labels map to the existing product-model permissions.
        # This remains a server-side authorization model, not an identity provider.
        "Owner": {"manage_members", "create_project", "view_project", "approve_deliverable", "view_quality", "upload_material", "view_evidence", "create_meeting"},
        "Member": {"create_task", "upload_material", "view_evidence", "create_meeting"},
    }
    project_statuses = {"Planning", "Researching", "Reviewing", "Delivering", "Completed"}
    scope_permissions = {"Private", "Team", "Organization"}

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal, *, initialize: bool = True) -> None:
        if initialize:
            initialize_database()
        self._session_factory = session_factory

    def create_org(self, name: str, admin: str) -> dict[str, object]:
        session = self._session_factory()
        try:
            org = Organization(name=name.strip())
            session.add(org)
            session.flush()
            member = OrganizationMember(organization_id=org.id, display_name=admin.strip(), role="Admin")
            session.add(member)
            self._record(session, org.id, admin, "organization_created", "创建 Organization Workspace")
            session.commit()
            return {"id": org.id, "name": org.name, "admin_member_id": member.id}
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def members(self, organization_id: str) -> list[dict[str, object]]:
        session = self._session_factory()
        try:
            self._require_org(session, organization_id)
            return [self._member_payload(item) for item in session.scalars(
                select(OrganizationMember).where(OrganizationMember.organization_id == organization_id)
            )]
        finally:
            session.close()

    def add_member(self, organization_id: str, actor_member_id: str, display_name: str, role: str) -> dict[str, object]:
        if role not in self.permissions:
            raise ValueError("不支持的组织角色。")
        session = self._session_factory()
        try:
            actor = self._member_with_permission(session, organization_id, actor_member_id, "manage_members")
            member = OrganizationMember(organization_id=organization_id, display_name=display_name.strip(), role=role)
            session.add(member)
            session.flush()
            self._record(session, organization_id, actor.display_name, "member_added", f"新增 {role} 成员：{member.display_name}")
            session.commit()
            return self._member_payload(member)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def check(self, organization_id: str, member_id: str, permission: str) -> OrganizationMember:
        session = self._session_factory()
        try:
            member = self._member_with_permission(session, organization_id, member_id, permission)
            session.expunge(member)
            return member
        finally:
            session.close()

    def activity(self, organization_id: str) -> list[dict[str, object]]:
        session = self._session_factory()
        try:
            self._require_org(session, organization_id)
            return [{"actor": item.actor, "role": self._role_for_actor(session, organization_id, item.actor),
                     "action": item.event_type, "target": item.summary, "timestamp": item.created_at}
                    for item in session.scalars(select(OrganizationActivity).where(
                        OrganizationActivity.organization_id == organization_id
                    ).order_by(OrganizationActivity.created_at.desc()))]
        finally:
            session.close()

    def create_project(self, organization_id: str, data: dict[str, object]) -> dict[str, object]:
        session = self._session_factory()
        try:
            actor = self._member_with_permission(session, organization_id, str(data["owner_member_id"]), "create_project")
            project = OrganizationProject(organization_id=organization_id,
                research_project_id=data.get("research_project_id") or None, workspace_id=data.get("workspace_id") or None,
                name=str(data["name"]).strip(), description=str(data.get("description") or ""),
                research_goal=str(data.get("research_goal") or ""), owner_member_id=actor.id, status="Planning")
            session.add(project)
            session.flush()
            self._record(session, organization_id, actor.display_name, "project_created", f"创建项目：{project.name}")
            session.commit()
            return self._project_payload(session, project)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_projects(self, organization_id: str) -> list[dict[str, object]]:
        session = self._session_factory()
        try:
            self._require_org(session, organization_id)
            return [self._project_payload(session, item) for item in session.scalars(select(OrganizationProject).where(
                OrganizationProject.organization_id == organization_id
            ).order_by(OrganizationProject.updated_at.desc()))]
        finally:
            session.close()

    def update_project_status(self, organization_id: str, project_id: str, member_id: str, status: str) -> dict[str, object]:
        if status not in self.project_statuses:
            raise ValueError("不支持的企业项目状态。")
        session = self._session_factory()
        try:
            member = self._member_with_permission(session, organization_id, member_id, "view_project")
            project = self._require_project(session, organization_id, project_id)
            project.status = status
            self._record(session, organization_id, member.display_name, "project_status_updated", f"项目 {project.name} 更新为 {status}")
            session.commit()
            return self._project_payload(session, project)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_knowledge_scope(self, organization_id: str, data: dict[str, str]) -> dict[str, object]:
        scope = data["knowledge_scope"]
        if scope not in self.scope_permissions:
            raise ValueError("不支持的知识范围。")
        session = self._session_factory()
        try:
            member = self._member_with_permission(session, organization_id, data["member_id"], "upload_material")
            if session.get(Paper, data["paper_id"]) is None:
                raise EnterpriseNotFoundError("知识资料不存在，无法设置范围。")
            grant = session.scalar(select(KnowledgeAccessGrant).where(KnowledgeAccessGrant.paper_id == data["paper_id"]))
            if grant is None:
                grant = KnowledgeAccessGrant(paper_id=data["paper_id"])
                session.add(grant)
            grant.organization_id, grant.owner_member_id, grant.knowledge_scope = organization_id, member.id, scope
            self._record(session, organization_id, member.display_name, "knowledge_scope_updated", f"资料范围设为 {scope}")
            session.commit()
            return {"paper_id": grant.paper_id, "knowledge_scope": grant.knowledge_scope, "organization_id": grant.organization_id}
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def team_knowledge(self, organization_id: str, member_id: str) -> list[dict[str, object]]:
        session = self._session_factory()
        try:
            member = self._member_with_permission(session, organization_id, member_id, "view_evidence")
            grants = session.scalars(select(KnowledgeAccessGrant).where(KnowledgeAccessGrant.organization_id == organization_id))
            result = []
            for grant in grants:
                if grant.knowledge_scope == "Private" and grant.owner_member_id != member.id:
                    continue
                paper = session.get(Paper, grant.paper_id)
                if paper is None:
                    continue
                chunks = int(session.scalar(select(func.count(PaperChunk.id)).where(PaperChunk.paper_id == paper.paper_id)) or 0)
                result.append({"paper_id": paper.paper_id, "title": paper.title, "document_type": paper.document_type,
                    "analysis_status": paper.analysis_status, "quality_status": paper.quality_status,
                    "knowledge_scope": grant.knowledge_scope, "chunk_count": chunks})
            return result
        finally:
            session.close()

    def create_meeting(self, organization_id: str, data: dict[str, object]) -> dict[str, object]:
        session = self._session_factory()
        try:
            member = self._member_with_permission(session, organization_id, str(data["member_id"]), "create_meeting")
            notes = str(data["notes"]).strip()
            summary, decisions, actions = self._meeting_proposals(notes)
            meeting = OrganizationMeeting(organization_id=organization_id, project_id=data.get("project_id") or None,
                submitted_by_member_id=member.id, notes=notes, summary=summary,
                decisions_json=json.dumps(decisions, ensure_ascii=False), action_items_json=json.dumps(actions, ensure_ascii=False))
            session.add(meeting)
            self._record(session, organization_id, member.display_name, "meeting_proposal_created", "提交会议纪要，等待人工确认决策与行动项")
            session.commit()
            return self._meeting_payload(meeting)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dashboard(self, organization_id: str, member_id: str) -> dict[str, object]:
        session = self._session_factory()
        try:
            self._member_with_permission(session, organization_id, member_id, "view_quality")
            projects = list(session.scalars(select(OrganizationProject).where(OrganizationProject.organization_id == organization_id)))
            grant_count = int(session.scalar(select(func.count(KnowledgeAccessGrant.id)).where(KnowledgeAccessGrant.organization_id == organization_id)) or 0)
            evidence_count = int(session.scalar(select(func.count(PaperChunk.id)).join(KnowledgeAccessGrant, KnowledgeAccessGrant.paper_id == PaperChunk.paper_id).where(KnowledgeAccessGrant.organization_id == organization_id)) or 0)
            activity_count = int(session.scalar(select(func.count(OrganizationActivity.id)).where(OrganizationActivity.organization_id == organization_id)) or 0)
            workspace_ids = [item.workspace_id for item in projects if item.workspace_id]
            deliverables = int(session.scalar(select(func.count(ResearchDocumentRevision.id)).where(ResearchDocumentRevision.workspace_id.in_(workspace_ids))) or 0) if workspace_ids else 0
            return {"organization": self._org_payload(session, organization_id),
                    "projects": {"total": len(projects), "by_status": dict(Counter(item.status for item in projects))},
                    "research_activity": activity_count, "knowledge_assets": grant_count, "evidence_count": evidence_count,
                    "review_queue": sum(1 for item in projects if item.status in {"Reviewing", "Delivering"}),
                    "deliverable_progress": deliverables}
        finally:
            session.close()

    def delivery_package(self, organization_id: str, member_id: str) -> dict[str, object]:
        """Return a review-required FDE package from existing organization data only."""
        dashboard = self.dashboard(organization_id, member_id)
        projects = self.list_projects(organization_id)
        has_assets = bool(dashboard["knowledge_assets"] or dashboard["evidence_count"])
        return {
            "status": "draft_for_human_review",
            "human_confirmation_required": True,
            "customer_background": "待客户确认：当前 Organization Workspace 尚未记录客户背景。",
            "pain_point": "待客户确认：请结合客户资料补充业务痛点与资料边界。",
            "ai_solution": ["Organization Workspace", "Evidence-grounded Research Workflow", "Human Review"],
            "implementation_plan": ["确认成员角色与资料范围", "关联已有 Research Workspace 与企业项目", "在人工审核后生成交付物"],
            "risk_control": ["仅共享已授权资料", "Evidence 不足时不生成科研结论", "所有决策和行动项需人工确认"],
            "acceptance_criteria": [
                f"组织已记录 {dashboard['projects']['total']} 个真实企业项目。",
                f"团队知识范围已记录 {dashboard['knowledge_assets']} 项资料。",
                "审核与交付状态由负责人确认，不自动通过。",
            ],
            "data_boundary": "已基于当前组织数据库汇总。" if has_assets else "当前组织尚无可验证知识资料或 Evidence；本交付包仅提供实施框架，不含科研结论。",
            "project_summaries": [{"name": item["name"], "status": item["status"], "deliverable_status": item["deliverable_status"]} for item in projects],
        }

    @staticmethod
    def _meeting_proposals(notes: str) -> tuple[str, list[dict[str, str]], list[dict[str, str]]]:
        lines = [line.strip("- •\t ") for line in notes.splitlines() if line.strip()]
        summary = "；".join(lines[:3]) if lines else "会议纪要尚未包含可解析的内容。"
        decisions = [{"decision": line, "owner": "待指定", "deadline": "待确认", "status": "pending"} for line in lines if any(word in line.lower() for word in ("决定", "决议", "确认", "decision"))]
        actions = [{"action": line, "owner": "待指定", "deadline": "待确认", "status": "pending"} for line in lines if any(word in line.lower() for word in ("行动", "跟进", "负责", "action"))]
        return summary, decisions or [{"decision": "请人工从会议纪要中确认研究决策。", "owner": "待指定", "deadline": "待确认", "status": "pending"}], actions or [{"action": "请人工确认是否创建后续研究任务。", "owner": "待指定", "deadline": "待确认", "status": "pending"}]

    @staticmethod
    def _meeting_payload(meeting: OrganizationMeeting) -> dict[str, object]:
        return {"id": meeting.id, "summary": meeting.summary, "decisions": json.loads(meeting.decisions_json), "action_items": json.loads(meeting.action_items_json), "status": meeting.status, "human_confirmation_required": True}

    def _project_payload(self, session: Session, project: OrganizationProject) -> dict[str, object]:
        task_count = int(session.scalar(select(func.count(ResearchTask.id)).where(ResearchTask.project_id == project.research_project_id)) or 0) if project.research_project_id else 0
        evidence_count = sum(len(json.loads(item.evidence_refs or "[]")) for item in session.scalars(select(ResearchTask).where(ResearchTask.workspace_id == project.workspace_id))) if project.workspace_id else 0
        owner = session.get(OrganizationMember, project.owner_member_id)
        member_count = int(session.scalar(select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == project.organization_id)) or 0)
        revisions = int(session.scalar(select(func.count(ResearchDocumentRevision.id)).where(ResearchDocumentRevision.workspace_id == project.workspace_id)) or 0) if project.workspace_id else 0
        return {"id": project.id, "organization_id": project.organization_id, "name": project.name, "description": project.description, "research_goal": project.research_goal, "status": project.status, "owner": owner.display_name if owner else "Unknown", "owner_member_id": project.owner_member_id, "member_count": member_count, "evidence_count": evidence_count, "task_count": task_count, "review_status": "Pending" if project.status == "Reviewing" else "Not required", "deliverable_status": "Draft available" if revisions else "Not started", "workspace_id": project.workspace_id, "created_time": project.created_at, "updated_time": project.updated_at}

    def _org_payload(self, session: Session, organization_id: str) -> dict[str, object]:
        org = self._require_org(session, organization_id)
        return {"id": org.id, "name": org.name, "member_count": int(session.scalar(select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == org.id)) or 0)}

    @staticmethod
    def _member_payload(item: OrganizationMember) -> dict[str, object]:
        return {"id": item.id, "name": item.display_name, "role": item.role, "permissions": sorted(EnterpriseCollaborationService.permissions.get(item.role, set()))}

    @staticmethod
    def _require_org(session: Session, organization_id: str) -> Organization:
        org = session.get(Organization, organization_id)
        if org is None:
            raise EnterpriseNotFoundError("Organization Workspace 不存在。")
        return org

    def _require_project(self, session: Session, organization_id: str, project_id: str) -> OrganizationProject:
        project = session.get(OrganizationProject, project_id)
        if project is None or project.organization_id != organization_id:
            raise EnterpriseNotFoundError("企业项目不存在。")
        return project

    def _member_with_permission(self, session: Session, organization_id: str, member_id: str, permission: str) -> OrganizationMember:
        self._require_org(session, organization_id)
        member = session.get(OrganizationMember, member_id)
        if not member or member.organization_id != organization_id or permission not in self.permissions.get(member.role, set()):
            raise PermissionDeniedError("当前成员没有执行该企业协作操作的权限。")
        return member

    @staticmethod
    def _record(session: Session, organization_id: str, actor: str, event_type: str, summary: str) -> None:
        session.add(OrganizationActivity(organization_id=organization_id, actor=actor, event_type=event_type, summary=summary))

    @staticmethod
    def _role_for_actor(session: Session, organization_id: str, actor: str) -> str:
        member = session.scalar(select(OrganizationMember).where(OrganizationMember.organization_id == organization_id, OrganizationMember.display_name == actor))
        return member.role if member else "System"
