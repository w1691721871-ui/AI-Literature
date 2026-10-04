import unittest

from app.services.research_source_provider import ResearchSourceProviderRegistry


class ResearchSourceProviderTests(unittest.TestCase):
    def test_crossref_provider_normalizes_metadata_as_candidate_only(self):
        registry = ResearchSourceProviderRegistry(lambda _: {
            "message": {"items": [{
                "title": ["Low-carbon concrete study"], "DOI": "10.1000/example",
                "published": {"date-parts": [[2025, 4, 1]]},
            }]}
        })
        candidates = registry.selected().search("low carbon concrete", 5)
        self.assertEqual(candidates[0]["status"], "CANDIDATE")
        self.assertEqual(candidates[0]["source_provider"], "CROSSREF")
        self.assertEqual(candidates[0]["published"], "2025-4-1")
        self.assertNotIn("evidence", candidates[0])

    def test_provider_registry_is_explicit_allow_list(self):
        registry = ResearchSourceProviderRegistry(lambda _: {})
        self.assertEqual(registry.catalog()[0]["mode"], "READ_ONLY_METADATA")
        with self.assertRaises(ValueError):
            registry.selected("untrusted-source")


if __name__ == "__main__":
    unittest.main()
