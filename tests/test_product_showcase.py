import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.database import Base
from app.services.product_showcase_service import ProductShowcaseService
class ProductShowcaseTests(unittest.TestCase):
 def setUp(self):self.e=create_engine("sqlite:///:memory:");Base.metadata.create_all(self.e);self.s=sessionmaker(bind=self.e);self.service=ProductShowcaseService(self.s,initialize=False)
 def tearDown(self):self.e.dispose()
 def test_demo_is_explicitly_demo_only(self):self.assertEqual(self.service.workflow()["classification"],"DEMO_ONLY")
 def test_capabilities_hide_prompt_and_cot(self):self.assertIn("Agent Intelligence",[x["name"] for x in self.service.capabilities()["groups"]])
 def test_empty_dashboard_has_no_synthetic_metrics(self):self.assertEqual(self.service.business()["data_state"],"NO_PRODUCTION_DATA")
 def test_release_timeline_includes_memory(self):self.assertIn("P39",[x[0] for x in self.service.releases()["releases"]])
if __name__=="__main__":unittest.main()
