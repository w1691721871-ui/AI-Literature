import unittest
from app.services.evidence_validation_orchestrator import EvidenceValidationOrchestrator
from app.services.research_evidence_analyzer import ResearchEvidenceAnalyzer
from app.services.research_brief_service import ResearchBriefService

class ResearchIntelligenceTests(unittest.TestCase):
 def test_candidates_do_not_auto_promote(self):
  result=EvidenceValidationOrchestrator().validate_candidates([{"source":"https://doi.org/x","title":"Low carbon concrete","confidence":.7,"validation_required":True}],"m")
  self.assertEqual(result["status"],"WAITING_REVIEW"); self.assertEqual(result["approved_evidence"],[])
 def test_insight_requires_approved_evidence(self):
  insight=ResearchEvidenceAnalyzer().analyze([],"low carbon concrete")
  self.assertEqual(insight["status"],"INSUFFICIENT_EVIDENCE"); self.assertIsNone(ResearchBriefService().draft("q",insight))
 def test_approved_evidence_creates_reviewable_brief(self):
  evidence=[{"status":"APPROVED","source":"https://doi.org/a","title":"Low carbon recycled concrete lifecycle","confidence":.8},{"status":"VERIFIED","source":"https://doi.org/b","title":"Low carbon concrete durability","confidence":.7}]
  insight=ResearchEvidenceAnalyzer().analyze(evidence,"low carbon materials")
  brief=ResearchBriefService().draft("low carbon materials",insight)
  self.assertEqual(insight["status"],"EVIDENCE_BOUND_INSIGHT"); self.assertEqual(brief["status"],"NEEDS_REVIEW")
