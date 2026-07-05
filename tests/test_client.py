"""Offline unit tests for promptctl (stdlib unittest — no network, no deps)."""

import unittest

from promptctl.client import PromptClient

PROMPTS = {
    "api": "devopsaitoolkit",
    "version": "v1",
    "resource": "prompts",
    "count": 3,
    "items": [
        {
            "id": "kubernetes-crashloopbackoff-triage",
            "title": "Kubernetes CrashLoopBackOff Triage Prompt",
            "category": "kubernetes-helm",
            "difficulty": "Advanced",
            "tools": ["Claude", "ChatGPT"],
            "tags": ["kubernetes", "troubleshooting"],
            "useCase": "Diagnose a pod stuck in CrashLoopBackOff.",
            "targetUser": "SREs",
            "prompt": "You are a senior SRE. Diagnose this CrashLoopBackOff...",
            "safetyNotes": ["Do not kubectl delete without a backup."],
            "url": "https://devopsaitoolkit.com/prompts/kubernetes-crashloopbackoff-triage/",
            "pubDate": "2026-01-01",
        },
        {
            "id": "terraform-plan-review",
            "title": "Terraform Plan Review Prompt",
            "category": "terraform",
            "difficulty": "Intermediate",
            "tools": ["Claude"],
            "tags": ["terraform", "iac"],
            "useCase": "Review a terraform plan for risk before apply.",
            "targetUser": "Platform engineers",
            "prompt": "Review this terraform plan for blast radius...",
            "safetyNotes": [],
            "url": "https://devopsaitoolkit.com/prompts/terraform-plan-review/",
            "pubDate": "2026-02-01",
        },
        {
            "id": "openstack-nova-scheduler-debug",
            "title": "OpenStack Nova Scheduler Debug Prompt",
            "category": "openstack",
            "difficulty": "Advanced",
            "tools": ["ChatGPT"],
            "tags": ["openstack", "nova"],
            "useCase": "Debug NoValidHost scheduler failures.",
            "targetUser": "Cloud operators",
            "prompt": "Debug this Nova scheduler NoValidHost error...",
            "safetyNotes": [],
            "url": "https://devopsaitoolkit.com/prompts/openstack-nova-scheduler-debug/",
            "pubDate": "2026-03-01",
        },
    ],
}

META = {
    "api": "devopsaitoolkit",
    "version": "v1",
    "counts": {"prompts": 3, "guides": 0, "errorGuides": 0},
    "categories": [
        {"slug": "kubernetes-helm", "name": "AI for Kubernetes & Helm", "prompts": 1},
        {"slug": "terraform", "name": "AI for Terraform", "prompts": 1},
        {"slug": "openstack", "name": "AI for OpenStack", "prompts": 1},
    ],
}


class FakeClient(PromptClient):
    """PromptClient with the network swapped for in-memory fixtures."""

    def __init__(self):
        super().__init__(cache=False)

    def fetch(self, path, refresh=False):
        if path == "meta.json":
            return META
        if path == "prompts.json":
            return PROMPTS
        if path.startswith("prompts/"):
            cat = path[len("prompts/"):-len(".json")]
            items = [p for p in PROMPTS["items"] if p["category"] == cat]
            return {"items": items}
        raise AssertionError(f"unexpected path {path}")


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.c = FakeClient()

    def test_keyword_all_terms_must_match(self):
        # matches title/useCase
        r = self.c.search("crashloopbackoff")
        self.assertEqual([p["id"] for p in r], ["kubernetes-crashloopbackoff-triage"])
        # matches inside the prompt body
        r = self.c.search("blast radius")
        self.assertEqual([p["id"] for p in r], ["terraform-plan-review"])
        # a word that appears nowhere -> no match
        self.assertEqual(self.c.search("nonexistentxyz"), [])

    def test_empty_query_returns_all(self):
        self.assertEqual(len(self.c.search("")), 3)

    def test_category_filter(self):
        r = self.c.search("", category="openstack")
        self.assertEqual([p["id"] for p in r], ["openstack-nova-scheduler-debug"])

    def test_difficulty_and_tool_filters(self):
        r = self.c.search("", difficulty="advanced")
        self.assertEqual({p["id"] for p in r},
                         {"kubernetes-crashloopbackoff-triage", "openstack-nova-scheduler-debug"})
        r = self.c.search("", tool="claude")
        self.assertEqual({p["id"] for p in r},
                         {"kubernetes-crashloopbackoff-triage", "terraform-plan-review"})

    def test_tag_filter(self):
        r = self.c.search("", tag="nova")
        self.assertEqual([p["id"] for p in r], ["openstack-nova-scheduler-debug"])

    def test_get_and_categories(self):
        self.assertEqual(self.c.get("terraform-plan-review")["title"], "Terraform Plan Review Prompt")
        self.assertIsNone(self.c.get("does-not-exist"))
        self.assertEqual(len(self.c.categories()), 3)


if __name__ == "__main__":
    unittest.main()
