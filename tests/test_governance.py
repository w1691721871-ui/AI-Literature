import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.organization import Organization
from app.models.governance import GovernanceWorkspace,WorkspaceUserRole,AuditLog,AgentPolicy
from app.services.governance_service import GovernanceError,GovernanceService
class GovernanceTests(unittest.TestCase):
 def setUp(self):
  self.e=create_engine('sqlite:///:memory:');self.S=sessionmaker(bind=self.e)
  for t in (Organization.__table__,GovernanceWorkspace.__table__,WorkspaceUserRole.__table__,AuditLog.__table__,AgentPolicy.__table__):t.create(self.e)
  self.x=GovernanceService(self.S,initialize=False);self.org=self.x.create_org('Lab A','owner')
 def tearDown(self):self.e.dispose()
 def test_isolation_rbac_audit_policy(self):
  ws=self.org['workspace_id'];self.assertEqual(self.x.permissions.check(ws,'owner','MISSION_CREATE')['role'],'OWNER')
  self.x.set_role(ws,'reviewer','REVIEWER','owner');self.assertTrue(self.x.permissions.check(ws,'reviewer','ARTIFACT_REVIEW')['allowed'])
  with self.assertRaises(GovernanceError):self.x.permissions.check(ws,'reviewer','CONNECTOR_ACCESS')
  policy=self.x.policy(ws,{'max_iterations':5,'max_tool_calls':12,'require_human_review':True,'allowed_connectors':['c1']},'owner');self.assertEqual(policy['max_iterations'],5)
  self.assertTrue(self.x.logs(ws));self.assertEqual(len(self.x.workspaces(self.org['id'])),1)
if __name__=='__main__':unittest.main()
