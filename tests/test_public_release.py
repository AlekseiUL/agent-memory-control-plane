import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_URLS = {
    "https://youtube.com/@alekseiulianov",
    "https://t.me/Sprut_AI",
    "https://t.me/+eH-qNIDmud8zNDZi",
    "https://t.me/tribute/app?startapp=sJyg",
    "https://github.com/AlekseiUL",
}
DOCS = {
    "architecture.md",
    "source-hierarchy.md",
    "privacy-threat-model.md",
    "memory-lifecycle.md",
    "team-interaction.md",
    "comparison-boundaries.md",
    "verification-rollback.md",
}


def load_public_scan():
    path = ROOT / "scripts" / "public_scan.py"
    spec = importlib.util.spec_from_file_location("amcp_public_scan", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublicReleaseTests(unittest.TestCase):
    def test_bilingual_readmes_have_diagram_boundaries_and_resources(self):
        english = (ROOT / "README.md").read_text(encoding="utf-8")
        russian = (ROOT / "README.ru.md").read_text(encoding="utf-8")
        for text in (english, russian):
            self.assertIn("```mermaid", text)
            self.assertIn("SQLite", text)
            self.assertIn("FTS5", text)
            for url in PUBLIC_URLS:
                self.assertIn(url, text)
        self.assertIn("Полное описание на русском", english)
        self.assertIn("По-русски", english)
        self.assertIn("Full English description", russian)
        self.assertIn("never", english.lower())
        self.assertIn("никогда", russian.lower())

    def test_documentation_has_complete_english_and_russian_sets(self):
        for name in DOCS:
            self.assertTrue((ROOT / "docs" / name).is_file(), name)
            self.assertTrue((ROOT / "docs" / "en" / name).is_file(), name)

    def test_public_scan_rejects_private_identifiers_and_allows_public_links(self):
        scanner = load_public_scan()
        private_cases = (
            "/" + "Users" + "/private-user/project",
            "owner" + "@" + "private.example.com",
            "Aleksei" + " Ulianov",
            "277" + "478969",
        )
        for value in private_cases:
            with self.subTest(value=value):
                self.assertTrue(scanner.scan_text("fixture", value))
        public_text = "\n".join(sorted(PUBLIC_URLS))
        self.assertEqual(scanner.scan_text("public-resources", public_text), [])

    def test_commit_identity_policy_is_generic(self):
        scanner = load_public_scan()
        self.assertEqual(
            scanner.GENERIC_IDENTITIES,
            {("AMCP Contributors", "noreply@example.invalid")},
        )


if __name__ == "__main__":
    unittest.main()
