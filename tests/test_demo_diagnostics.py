import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.ai_mission import AIMission
from app.models.solution_project import SolutionProject
from app.services.database import Base
from scripts.demo_diagnostics import mission_review_statuses


class DemoDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_mission_review_summary_uses_persisted_review_states_and_workspace_scope(self):
        session = self.sessions()
        session.add_all([
            AIMission(id="pending", workspace_id="demo", title="Pending", goal="Goal", status="WAITING_REVIEW"),
            AIMission(id="revision", workspace_id="demo", title="Revision", goal="Goal", status="NEEDS_REVISION"),
            AIMission(id="approved", workspace_id="demo", title="Approved", goal="Goal", status="APPROVED"),
            AIMission(id="unreviewed", workspace_id="demo", title="Unreviewed", goal="Goal", status="PLANNING"),
            AIMission(id="foreign", workspace_id="other", title="Foreign", goal="Goal", status="NEEDS_REVISION"),
        ])
        session.commit()
        session.close()

        self.assertEqual(
            mission_review_statuses(self.sessions, "demo"),
            {"PENDING": 1, "NEEDS_REVISION": 1, "APPROVED": 1, "REJECTED": 0},
        )


if __name__ == "__main__":
    unittest.main()
