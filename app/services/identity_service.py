"""Password-safe identity and session services for enterprise API boundaries."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models.governance import AgentPolicy, GovernanceWorkspace, WorkspaceUserRole
from app.models.identity import User, UserSession
from app.models.organization import Organization
from app.services.database import SessionLocal, initialize_database


class IdentityError(ValueError):
    pass


@dataclass(frozen=True)
class IdentityContext:
    user_id: str
    email: str
    display_name: str
    workspace_id: str
    role: str
    session_id: str


class IdentityService:
    """Stores only salted password hashes and hashes of opaque session tokens."""

    @staticmethod
    def _session_lifetime() -> timedelta:
        """Use a bounded deployment setting for opaque server-side sessions."""
        try:
            seconds = int(os.getenv("TOKEN_EXPIRE", "43200"))
        except ValueError:
            seconds = 43200
        return timedelta(seconds=max(900, min(seconds, 604800)))
    demo_organization_name = "ResearchOS Demo Organization"
    demo_workspace_name = "ResearchOS Demo Workspace"
    demo_email = "demo_user@researchos.demo"

    def __init__(self, sessions=SessionLocal, *, initialize=True):
        if initialize:
            initialize_database()
        self._sessions = sessions

    def register(self, email: str, display_name: str, password: str) -> dict[str, object]:
        normalized = email.strip().lower()
        if "@" not in normalized or len(normalized) > 320:
            raise IdentityError("请输入有效邮箱地址。")
        if not display_name.strip() or len(display_name.strip()) > 160:
            raise IdentityError("请输入有效显示名称。")
        if len(password) < 12:
            raise IdentityError("密码至少需要 12 个字符。")
        session = self._sessions()
        try:
            if session.scalar(select(User).where(User.email == normalized)):
                raise IdentityError("该邮箱已存在。")
            user = User(email=normalized, display_name=display_name.strip(), password_hash=self._password_hash(password))
            session.add(user); session.commit(); session.refresh(user)
            return self._user(user)
        finally:
            session.close()

    def register_workspace(self, email: str, display_name: str, password: str, workspace_name: str) -> dict[str, object]:
        """Create a personal enterprise boundary and immediately issue its Session.

        The browser provides no role or workspace identifier: the server creates
        the Workspace and binds its creator as OWNER in the same transaction.
        """
        normalized_workspace = workspace_name.strip()
        if not normalized_workspace or len(normalized_workspace) > 160:
            raise IdentityError("请输入有效 Workspace 名称。")
        normalized = email.strip().lower()
        if "@" not in normalized or len(normalized) > 320:
            raise IdentityError("请输入有效邮箱地址。")
        if not display_name.strip() or len(display_name.strip()) > 160:
            raise IdentityError("请输入有效显示名称。")
        if len(password) < 12:
            raise IdentityError("密码至少需要 12 个字符。")

        session = self._sessions()
        try:
            if session.scalar(select(User).where(User.email == normalized)):
                raise IdentityError("该邮箱已存在。")
            user = User(email=normalized, display_name=display_name.strip(), password_hash=self._password_hash(password))
            session.add(user)
            session.flush()
            organization = Organization(name=f"{normalized_workspace} Organization")
            session.add(organization)
            session.flush()
            workspace = GovernanceWorkspace(
                organization_id=organization.id,
                name=normalized_workspace,
                owner_id=user.id,
            )
            session.add(workspace)
            session.flush()
            created_workspace_id = workspace.id
            session.add(WorkspaceUserRole(workspace_id=workspace.id, user_id=user.id, role="OWNER"))
            session.add(AgentPolicy(workspace_id=workspace.id))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        return self._session_response(email=normalized, password=password, workspace_id=created_workspace_id)

    def create_demo_session(self) -> dict[str, object]:
        """Issue an isolated, explicitly demo-only MEMBER Session.

        It never reuses a customer Workspace and never elevates the demo user.
        The randomized password is retained only as a salted hash, then discarded.
        """
        session = self._sessions()
        try:
            user = session.scalar(select(User).where(User.email == self.demo_email))
            if not user:
                user = User(
                    email=self.demo_email,
                    display_name="demo_user",
                    password_hash=self._password_hash(secrets.token_urlsafe(48)),
                )
                session.add(user)
                session.flush()
            organization = session.scalar(select(Organization).where(Organization.name == self.demo_organization_name))
            if not organization:
                organization = Organization(name=self.demo_organization_name)
                session.add(organization)
                session.flush()
            workspace = session.scalar(select(GovernanceWorkspace).where(
                GovernanceWorkspace.organization_id == organization.id,
                GovernanceWorkspace.name == self.demo_workspace_name,
            ))
            if not workspace:
                workspace = GovernanceWorkspace(
                    organization_id=organization.id,
                    name=self.demo_workspace_name,
                    owner_id=user.id,
                )
                session.add(workspace)
                session.flush()
                session.add(AgentPolicy(workspace_id=workspace.id))
            membership = session.scalar(select(WorkspaceUserRole).where(
                WorkspaceUserRole.workspace_id == workspace.id,
                WorkspaceUserRole.user_id == user.id,
            ))
            if not membership:
                membership = WorkspaceUserRole(workspace_id=workspace.id, user_id=user.id, role="MEMBER")
                session.add(membership)
            elif membership.role != "MEMBER":
                membership.role = "MEMBER"
            session.flush()
            response = self._issue_session(session, user, "MEMBER", workspace.id)
            session.commit()
            return response
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_session(self, email: str, password: str, workspace_id: str | None = None) -> dict[str, object]:
        return self._session_response(email=email, password=password, workspace_id=workspace_id)

    def _session_response(self, email: str, password: str, workspace_id: str | None = None) -> dict[str, object]:
        session = self._sessions()
        try:
            user = session.scalar(select(User).where(User.email == email.strip().lower()))
            if not user or user.status != "ACTIVE" or not self._verify_password(password, user.password_hash):
                raise IdentityError("登录信息无效。")
            memberships = list(session.scalars(
                select(WorkspaceUserRole).where(WorkspaceUserRole.user_id == user.id)
            ).all())
            if workspace_id:
                memberships = [item for item in memberships if item.workspace_id == workspace_id]
            if not memberships:
                raise IdentityError("该用户没有可访问的 Workspace。")
            # The initial Workspace is chosen only from persisted memberships.
            # A browser never supplies this identity boundary as an authority.
            role = sorted(memberships, key=lambda item: item.workspace_id)[0]
            workspace_id = role.workspace_id
            workspace = session.get(GovernanceWorkspace, workspace_id)
            if not workspace:
                raise IdentityError("Workspace 不可用。")
            response = self._issue_session(session, user, role.role, workspace_id)
            session.commit()
            return response
        finally:
            session.close()

    def context_for_token(self, token: str) -> IdentityContext:
        if not token:
            raise IdentityError("需要有效登录 Session。")
        session = self._sessions()
        try:
            row = session.scalar(select(UserSession).where(UserSession.session_token_hash == self._token_hash(token)))
            expires_at = row.expires_at.replace(tzinfo=timezone.utc) if row and row.expires_at.tzinfo is None else (row.expires_at if row else None)
            if not row or expires_at <= datetime.now(timezone.utc):
                raise IdentityError("Session 无效或已过期。")
            user = session.get(User, row.user_id)
            role = session.scalar(select(WorkspaceUserRole).where(WorkspaceUserRole.workspace_id == row.workspace_id, WorkspaceUserRole.user_id == row.user_id))
            if not user or user.status != "ACTIVE" or not role:
                raise IdentityError("Session 不再具备 Workspace 访问权限。")
            return self._context(user, role.role, row.workspace_id, row.id)
        finally:
            session.close()

    def switch_workspace(self, context: IdentityContext, workspace_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            role = session.scalar(select(WorkspaceUserRole).where(WorkspaceUserRole.workspace_id == workspace_id, WorkspaceUserRole.user_id == context.user_id))
            if not role or not session.get(GovernanceWorkspace, workspace_id):
                raise IdentityError("该用户无权切换到所选 Workspace。")
            row = session.get(UserSession, context.session_id)
            if not row:
                raise IdentityError("Session 无效。")
            row.workspace_id = workspace_id; session.commit()
            user = session.get(User, context.user_id)
            return {"profile": self._context(user, role.role, workspace_id, row.id)}
        finally:
            session.close()

    def profile(self, context: IdentityContext) -> dict[str, object]:
        session = self._sessions()
        try:
            workspaces = []
            for membership in session.scalars(select(WorkspaceUserRole).where(WorkspaceUserRole.user_id == context.user_id)).all():
                workspace = session.get(GovernanceWorkspace, membership.workspace_id)
                if workspace:
                    workspaces.append({"id": workspace.id, "name": workspace.name, "role": membership.role, "organization_id": workspace.organization_id, "is_demo": self._is_demo_workspace(workspace)})
            current_workspace = next((item for item in workspaces if item["id"] == context.workspace_id), None)
            return {
                "user": {"id": context.user_id, "email": context.email, "display_name": context.display_name},
                "workspace": {
                    "id": context.workspace_id,
                    "name": current_workspace["name"] if current_workspace else "Authorized Workspace",
                    "role": context.role,
                    "is_demo": bool(current_workspace and current_workspace["is_demo"]),
                    "member_count": int(session.scalar(
                        select(func.count(WorkspaceUserRole.id)).where(
                            WorkspaceUserRole.workspace_id == context.workspace_id
                        )
                    ) or 0),
                },
                "workspaces": workspaces,
            }
        finally:
            session.close()

    @staticmethod
    def _password_hash(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        return f"scrypt${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"

    @staticmethod
    def _verify_password(password: str, stored: str) -> bool:
        try:
            algorithm, salt_text, digest_text = stored.split("$", 2)
            if algorithm != "scrypt":
                return False
            digest = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt_text), n=2**14, r=8, p=1)
            return hmac.compare_digest(digest, base64.b64decode(digest_text))
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _user(user: User) -> dict[str, object]:
        return {"id": user.id, "email": user.email, "display_name": user.display_name, "status": user.status, "created_at": user.created_at}

    def _issue_session(self, session, user: User, role: str, workspace_id: str) -> dict[str, object]:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + self._session_lifetime()
        row = UserSession(
            user_id=user.id,
            workspace_id=workspace_id,
            session_token_hash=self._token_hash(token),
            expires_at=expires_at,
        )
        session.add(row)
        session.flush()
        workspace = session.get(GovernanceWorkspace, workspace_id)
        return {
            "session_token": token,
            "expires_at": expires_at,
            "user": self._user(user),
            "workspace": {
                "id": workspace_id,
                "name": workspace.name if workspace else "Authorized Workspace",
                "role": role,
                "is_demo": bool(workspace and self._is_demo_workspace(workspace)),
            },
            "profile": self._context(user, role, workspace_id, row.id),
        }

    def _is_demo_workspace(self, workspace: GovernanceWorkspace) -> bool:
        return workspace.name == self.demo_workspace_name

    @staticmethod
    def _context(user: User, role: str, workspace_id: str, session_id: str) -> IdentityContext:
        return IdentityContext(user.id, user.email, user.display_name, workspace_id, role, session_id)
