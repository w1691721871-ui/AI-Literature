"""Opt-in demo identity provisioning for isolated demo deployments only."""
from __future__ import annotations

import os
from sqlalchemy import select

from app.models.governance import GovernanceWorkspace, WorkspaceUserRole
from app.models.identity import User
from app.models.organization import Organization
from app.services.database import SessionLocal, initialize_database
from app.services.identity_service import IdentityService


class DemoIdentitySeeder:
    """Creates no identity unless DEMO_MODE is explicitly enabled.

    Passwords are supplied by the deployment environment. They are never
    embedded in source, responses, logs, or frontend bundles.
    """

    def __init__(self, sessions=SessionLocal, *, initialize=True):
        if initialize:
            initialize_database()
        self._sessions = sessions
        self._identity = IdentityService(sessions, initialize=False)

    @staticmethod
    def enabled() -> bool:
        return os.getenv("DEMO_MODE", "false").strip().lower() == "true"

    def seed_if_enabled(self) -> dict[str, object]:
        if not self.enabled():
            return {"seeded": False, "reason": "DEMO_MODE_DISABLED"}
        owner_password = os.getenv("DEMO_OWNER_PASSWORD", "")
        reviewer_password = os.getenv("DEMO_REVIEWER_PASSWORD", "")
        if not owner_password or not reviewer_password:
            return {"seeded": False, "reason": "DEMO_CREDENTIALS_NOT_CONFIGURED"}
        owner = self._ensure_user(
            os.getenv("DEMO_OWNER_EMAIL", "demo.owner@localhost"),
            os.getenv("DEMO_OWNER_NAME", "Demo Owner"), owner_password,
        )
        reviewer = self._ensure_user(
            os.getenv("DEMO_REVIEWER_EMAIL", "demo.reviewer@localhost"),
            os.getenv("DEMO_REVIEWER_NAME", "Demo Reviewer"), reviewer_password,
        )
        session = self._sessions()
        try:
            workspace = session.scalar(select(GovernanceWorkspace).where(GovernanceWorkspace.name == "Demo Workspace"))
            if not workspace:
                organization = Organization(name="ResearchOS Demo Organization")
                session.add(organization); session.flush()
                workspace = GovernanceWorkspace(organization_id=organization.id, name="Demo Workspace", owner_id=owner["id"])
                session.add(workspace); session.flush()
            for user, role in ((owner, "OWNER"), (reviewer, "REVIEWER")):
                membership = session.scalar(select(WorkspaceUserRole).where(
                    WorkspaceUserRole.workspace_id == workspace.id,
                    WorkspaceUserRole.user_id == user["id"],
                ))
                if not membership:
                    session.add(WorkspaceUserRole(workspace_id=workspace.id, user_id=user["id"], role=role))
            session.commit()
            return {"seeded": True, "workspace_id": workspace.id}
        finally:
            session.close()

    def _ensure_user(self, email: str, display_name: str, password: str) -> dict[str, object]:
        session = self._sessions()
        try:
            user = session.scalar(select(User).where(User.email == email.strip().lower()))
            if user:
                return {"id": user.id, "email": user.email}
        finally:
            session.close()
        return self._identity.register(email, display_name, password)
