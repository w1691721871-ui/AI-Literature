"""Small SQLite setup for the local research paper library."""

from collections.abc import Generator
import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORK_DIRECTORY = PROJECT_ROOT / "work"
DATABASE_PATH = WORK_DIRECTORY / "research_library.db"
# Deployment may supply an external-compatible URL later; local development
# remains intentionally SQLite-compatible. No credential value is logged.
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH.as_posix()}")


class Base(DeclarativeBase):
    """Base class shared by all local SQLite models."""


def _build_engine():
    """Create the SQLite engine after ensuring its ignored work directory exists."""
    WORK_DIRECTORY.mkdir(parents=True, exist_ok=True)
    return create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def initialize_database() -> None:
    """Create local paper-library and report-history tables when first used."""
    # Importing models registers them with Base.metadata without a circular import.
    from app.models.analysis_record import AnalysisRecord  # noqa: F401
    from app.models.agent_trace import AgentTrace  # noqa: F401
    from app.models.agent_metric import AgentMetric  # noqa: F401
    from app.models.agent_evaluation import AgentEvaluation  # noqa: F401
    from app.models.agent_memory import AgentMemory  # noqa: F401
    from app.models.execution_graph import ExecutionGraph  # noqa: F401
    from app.models.planner_trace import PlannerTrace  # noqa: F401
    from app.models.adaptive_iteration import AdaptiveIteration  # noqa: F401
    from app.models.copilot_session import CopilotSession  # noqa: F401
    from app.models.copilot_message import CopilotMessage  # noqa: F401
    from app.models.file_asset import FileAsset  # noqa: F401
    from app.models.document_summary import DocumentSummary  # noqa: F401
    from app.models.document_requirement import DocumentRequirement  # noqa: F401
    from app.models.mission_file_source import MissionFileSource  # noqa: F401
    from app.models.artifact import Artifact, ArtifactVersion, ArtifactEvidence  # noqa: F401
    from app.models.connector import Connector, DataSource, ConnectorTrace, MissionDataSource, ArtifactDataSource  # noqa: F401
    from app.models.agent_collaboration import AgentMessage, CollaborationGraph, AgentConflict  # noqa: F401
    from app.models.governance import GovernanceWorkspace, WorkspaceUserRole, AuditLog, AgentPolicy  # noqa: F401
    from app.models.runtime_task import RuntimeTask  # noqa: F401
    from app.models.runtime_execution import RuntimeExecution  # noqa: F401
    from app.models.mission_contract import MissionContract, RuntimeExecutionState  # noqa: F401
    from app.models.approval import ApprovalRequest  # noqa: F401
    from app.models.audit import AuditEvent  # noqa: F401
    from app.models.identity import User, UserSession  # noqa: F401
    from app.models.agent_observation import AgentObservation  # noqa: F401
    from app.models.prompt_template import PromptTemplate  # noqa: F401
    from app.models.benchmark import BenchmarkTask, BenchmarkRun, BenchmarkScore, AgentVersion  # noqa: F401
    from app.models.enterprise_scenario import EnterpriseScenario, ScenarioRun, DemoDataSource  # noqa: F401
    from app.models.workspace_experience import ActivityEvent, ArtifactComment  # noqa: F401
    from app.models.enterprise_memory import DecisionRecord, KnowledgeAsset  # noqa: F401
    from app.models.advanced_computer import ComputerEnvironment, ComputerPlan, ComputerObservation, ComputerExperience  # noqa: F401
    from app.models.computer_vision import ComputerVisionObservation, ComputerUIElement, ComputerSimulationSession  # noqa: F401
    from app.models.enterprise_scenario import EnterpriseScenario, ScenarioRun, DemoDataSource  # noqa: F401
    from app.models.autonomous_research_run import AutonomousResearchRun  # noqa: F401
    from app.models.research_memory import ResearchMemory  # noqa: F401
    from app.models.research_worker_run import ResearchWorkerRun  # noqa: F401
    from app.models.research_worker_context import ResearchWorkerContext  # noqa: F401
    from app.models.research_workspace import ResearchWorkspace  # noqa: F401
    from app.models.research_task import ResearchTask  # noqa: F401
    from app.models.operator_task import OperatorTask  # noqa: F401
    from app.models.operator_action import OperatorAction  # noqa: F401
    from app.models.computer_session import ComputerSession  # noqa: F401
    from app.models.computer_action import ComputerAction  # noqa: F401
    from app.models.computer_execution_event import ComputerExecutionEvent  # noqa: F401
    from app.models.code_patch import CodePatch  # noqa: F401
    from app.models.computer_task_checkpoint import ComputerTaskCheckpoint  # noqa: F401
    from app.models.computer_runtime_session import ComputerRuntimeSession  # noqa: F401
    from app.models.computer_artifact import ComputerArtifact  # noqa: F401
    from app.models.computer_recovery_attempt import ComputerRecoveryAttempt  # noqa: F401
    from app.models.computer_file_change import ComputerFileChange  # noqa: F401
    from app.models.computer_activity_summary import ComputerActivitySummary  # noqa: F401
    from app.models.computer_project_memory import ComputerProjectMemory  # noqa: F401
    from app.models.computer_mission import ComputerMission  # noqa: F401
    from app.models.user_onboarding_state import UserOnboardingState  # noqa: F401
    from app.models.solution_project import SolutionProject  # noqa: F401
    from app.models.solution_requirement import SolutionRequirement  # noqa: F401
    from app.models.solution_deliverable import SolutionDeliverable  # noqa: F401
    from app.models.solution_computer_mission import SolutionComputerMission  # noqa: F401
    from app.models.solution_version import SolutionVersion  # noqa: F401
    from app.models.ai_mission import AIMission, AIMissionEvent  # noqa: F401
    from app.models.notification import Notification  # noqa: F401
    from app.models.research_copilot_action import ResearchCopilotAction  # noqa: F401
    from app.models.research_document_revision import ResearchDocumentRevision  # noqa: F401
    from app.models.research_workflow import ResearchWorkflow, WorkflowEvent, WorkflowStep  # noqa: F401
    from app.models.organization import (  # noqa: F401
        Organization, OrganizationMember, OrganizationActivity, OrganizationProject,
        KnowledgeAccessGrant, OrganizationMeeting,
    )
    from app.models.paper import Paper  # noqa: F401
    from app.models.paper_chunk import PaperChunk  # noqa: F401
    from app.models.research_project import ResearchProject  # noqa: F401
    from app.models.research_action import ResearchAction  # noqa: F401
    from app.models.research_decision import ResearchDecision  # noqa: F401
    from app.models.research_outcome import ResearchOutcome  # noqa: F401
    from app.models.rag_query_record import RagQueryRecord  # noqa: F401
    from app.models.mission_state import MissionState  # noqa: F401
    from app.models.computer_environment import ComputerEnvironmentState  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()


def _apply_lightweight_migrations() -> None:
    """Add small SQLite columns safely for local projects created before RAG v3."""
    columns = {column["name"] for column in inspect(engine).get_columns("papers")}
    if "quality_status" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE papers ADD COLUMN quality_status VARCHAR(50) NOT NULL DEFAULT 'parsed'")
            )
    if "document_type" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE papers ADD COLUMN document_type VARCHAR(50) NOT NULL DEFAULT 'paper'")
            )
    action_columns = {column["name"] for column in inspect(engine).get_columns("research_actions")}
    if "rationale" not in action_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE research_actions ADD COLUMN rationale TEXT NOT NULL DEFAULT ''")
            )
    outcome_columns = {column["name"] for column in inspect(engine).get_columns("research_outcomes")}
    if "source_action_id" not in outcome_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE research_outcomes ADD COLUMN source_action_id VARCHAR(36)"))
    run_columns = {column["name"] for column in inspect(engine).get_columns("autonomous_research_runs")}
    run_additions = {
        "environment_profile": "TEXT NOT NULL DEFAULT '{}'",
        "memory_snapshot": "TEXT NOT NULL DEFAULT '{}'",
        "current_step": "VARCHAR(300) NOT NULL DEFAULT '等待执行'",
        "current_tool": "VARCHAR(100) NOT NULL DEFAULT ''",
        "completed_tasks": "TEXT NOT NULL DEFAULT '[]'",
        "next_plan": "TEXT NOT NULL DEFAULT '[]'",
        "failure_reason": "TEXT NOT NULL DEFAULT ''",
    }
    for name, definition in run_additions.items():
        if name not in run_columns:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE autonomous_research_runs ADD COLUMN {name} {definition}"))
    worker_columns = {column["name"] for column in inspect(engine).get_columns("research_worker_runs")}
    worker_additions = {
        "current_phase": "VARCHAR(40) NOT NULL DEFAULT 'planning'",
        "execution_history": "TEXT NOT NULL DEFAULT '[]'",
    }
    for name, definition in worker_additions.items():
        if name not in worker_columns:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE research_worker_runs ADD COLUMN {name} {definition}"))
    task_columns = {column["name"] for column in inspect(engine).get_columns("research_tasks")}
    task_additions = {
        "project_id": "VARCHAR(36)",
        "decision_id": "VARCHAR(36)",
        "evidence_refs": "TEXT NOT NULL DEFAULT '[]'",
    }
    for name, definition in task_additions.items():
        if name not in task_columns:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE research_tasks ADD COLUMN {name} {definition}"))
    mission_columns = {column["name"] for column in inspect(engine).get_columns("ai_missions")}
    mission_additions = {
        "workspace_id": "VARCHAR(36)",
        "solution_project_id": "VARCHAR(36)",
        "evidence_refs_json": "TEXT NOT NULL DEFAULT '[]'",
        "review_comment": "TEXT NOT NULL DEFAULT ''",
        "retry_count": "INTEGER NOT NULL DEFAULT 0",
        "adaptive_iteration": "INTEGER NOT NULL DEFAULT 0",
        "max_iterations": "INTEGER NOT NULL DEFAULT 3",
    }
    for name, definition in mission_additions.items():
        if name not in mission_columns:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE ai_missions ADD COLUMN {name} {definition}"))
    workspace_columns = {column["name"] for column in inspect(engine).get_columns("governance_workspaces")}
    if "owner_id" not in workspace_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE governance_workspaces ADD COLUMN owner_id VARCHAR(36)"))
    connector_columns = {column["name"] for column in inspect(engine).get_columns("connectors")}
    if "workspace_id" not in connector_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE connectors ADD COLUMN workspace_id VARCHAR(36)"))
    asset_columns = {column["name"] for column in inspect(engine).get_columns("knowledge_assets")}
    if "workspace_id" not in asset_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE knowledge_assets ADD COLUMN workspace_id VARCHAR(36)"))
    decision_columns = {column["name"] for column in inspect(engine).get_columns("decision_records")}
    if "workspace_id" not in decision_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE decision_records ADD COLUMN workspace_id VARCHAR(36)"))
    artifact_columns = {column["name"] for column in inspect(engine).get_columns("artifacts")}
    if "release_status" not in artifact_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE artifacts ADD COLUMN release_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT'"))
    version_columns = {column["name"] for column in inspect(engine).get_columns("solution_versions")}
    if "created_by" not in version_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE solution_versions ADD COLUMN created_by VARCHAR(80) NOT NULL DEFAULT 'AI'"))
    computer_mission_columns = {column["name"] for column in inspect(engine).get_columns("computer_missions")}
    computer_mission_additions = {
        "mission_id": "VARCHAR(36)", "task": "TEXT NOT NULL DEFAULT ''", "reason": "TEXT NOT NULL DEFAULT ''",
        "risk_level": "VARCHAR(30) NOT NULL DEFAULT 'LOW'", "status": "VARCHAR(40) NOT NULL DEFAULT 'CREATED'",
        "action_plan_json": "TEXT NOT NULL DEFAULT '[]'", "diff_content": "TEXT NOT NULL DEFAULT ''",
        "approval_status": "VARCHAR(40) NOT NULL DEFAULT 'PENDING'", "execution_allowed": "BOOLEAN NOT NULL DEFAULT 0",
        "workspace_profile_json": "TEXT NOT NULL DEFAULT '{}'", "execution_log_json": "TEXT NOT NULL DEFAULT '[]'",
        "verification_json": "TEXT NOT NULL DEFAULT '{}'", "retry_count": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, definition in computer_mission_additions.items():
        if name not in computer_mission_columns:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE computer_missions ADD COLUMN {name} {definition}"))
    trace_columns = {column["name"] for column in inspect(engine).get_columns("agent_traces")}
    trace_additions = {
        "mission_id": "VARCHAR(36)", "agent_name": "VARCHAR(100) NOT NULL DEFAULT 'Research Agent'",
        "action": "TEXT NOT NULL DEFAULT ''", "status": "VARCHAR(40) NOT NULL DEFAULT 'COMPLETED'",
        "duration": "FLOAT", "input_summary": "TEXT NOT NULL DEFAULT ''",
        "output_summary": "TEXT NOT NULL DEFAULT ''", "tool_used": "VARCHAR(100) NOT NULL DEFAULT ''",
        "evidence_count": "INTEGER NOT NULL DEFAULT 0",
        "iteration": "INTEGER NOT NULL DEFAULT 0", "decision": "VARCHAR(60) NOT NULL DEFAULT ''",
        "trigger": "VARCHAR(80) NOT NULL DEFAULT ''", "graph_version": "INTEGER NOT NULL DEFAULT 1",
        "model_name": "VARCHAR(100) NOT NULL DEFAULT ''", "latency": "FLOAT", "token_usage_summary": "VARCHAR(120) NOT NULL DEFAULT ''",
    }
    for name, definition in trace_additions.items():
        if name not in trace_columns:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE agent_traces ADD COLUMN {name} {definition}"))
    graph_columns = {column["name"] for column in inspect(engine).get_columns("execution_graphs")}
    for name, definition in {"version":"INTEGER NOT NULL DEFAULT 1", "parent_version":"INTEGER", "change_summary":"TEXT NOT NULL DEFAULT 'Initial plan'"}.items():
        if name not in graph_columns:
            with engine.begin() as connection: connection.execute(text(f"ALTER TABLE execution_graphs ADD COLUMN {name} {definition}"))
    evaluation_columns = {column["name"] for column in inspect(engine).get_columns("agent_evaluations")}
    if "planner_score" not in evaluation_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE agent_evaluations ADD COLUMN planner_score INTEGER NOT NULL DEFAULT 0"))
    for name, definition in {"adaptive_iterations":"INTEGER NOT NULL DEFAULT 0", "replan_count":"INTEGER NOT NULL DEFAULT 0", "evidence_retrieval_rounds":"INTEGER NOT NULL DEFAULT 0", "verification_rounds":"INTEGER NOT NULL DEFAULT 0", "final_decision":"VARCHAR(60) NOT NULL DEFAULT ''"}.items():
        if name not in evaluation_columns:
            with engine.begin() as connection: connection.execute(text(f"ALTER TABLE agent_evaluations ADD COLUMN {name} {definition}"))


def get_database_session() -> Generator[Session, None, None]:
    """Yield a short-lived database session for future FastAPI routes."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
