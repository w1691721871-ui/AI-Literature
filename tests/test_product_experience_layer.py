"""P20 fixtures use an isolated SQLite database; no knowledge-base records are created."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.computer_artifact import ComputerArtifact
from app.models.computer_mission import ComputerMission
from app.models.research_document_revision import ResearchDocumentRevision
from app.models.user_onboarding_state import UserOnboardingState
from app.services.product_experience_service import ProductExperienceService


class ProductExperienceLayerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        for table in (ComputerArtifact.__table__, ComputerMission.__table__, ResearchDocumentRevision.__table__, UserOnboardingState.__table__):
            table.create(self.engine)
        self.service = ProductExperienceService(self.Session, initialize=False)

    def tearDown(self):
        self.engine.dispose()

    def test_onboarding_is_local_and_completable(self):
        self.assertTrue(self.service.onboarding("fixture")["first_visit"])
        result = self.service.complete_onboarding_step("fixture", "welcome")
        self.assertFalse(result["first_visit"])
        self.assertEqual(result["completed_steps"], ["welcome"])

    def test_mission_lifecycle_is_linked_to_existing_task_id(self):
        mission = self.service.create_mission("task-a", "Optimize my frontend")
        self.assertEqual(mission["progress"], 20)
        result = self.service.update_mission("task-a", 70, "WAITING_APPROVAL")
        self.assertEqual(result["current_stage"], "WAITING_APPROVAL")

    def test_artifact_gallery_returns_only_persisted_records(self):
        session = self.Session()
        session.add(ComputerArtifact(runtime_id="runtime-a", artifact_type="PATCH", name="styles.css", status="WAITING_APPROVAL", metadata_json="{}"))
        session.commit(); session.close()
        gallery = self.service.artifacts()
        self.assertEqual(len(gallery), 1)
        self.assertEqual(gallery[0]["category"], "Computer")

    def test_demo_catalog_is_explicitly_bounded(self):
        demos = self.service.demo_scenarios()
        self.assertEqual(len(demos), 3)
        self.assertTrue(all("Demo" in item["boundary"] for item in demos))


if __name__ == "__main__":
    unittest.main()
