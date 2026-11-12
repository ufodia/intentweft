"""Check packaging regressions on disposable copies of the repository."""

import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("intentweft_repository_check", ROOT / "scripts" / "check_repository.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "repository"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))

    def test_complete_repository_passes(self):
        self.assertEqual(checker.check(self.root), [])

    def test_missing_description_is_rejected(self):
        path = self.root / "skills" / "intentweft" / "SKILL.md"
        path.write_text("---\nname: intentweft\n---\n# IntentWeft\n", encoding="utf-8")
        self.assertTrue(any("Invalid skill metadata" in error for error in checker.check(self.root)))

    def test_invalid_interface_quoting_is_rejected(self):
        path = self.root / "skills" / "intentweft" / "agents" / "openai.yaml"
        text = path.read_text(encoding="utf-8").replace('display_name: "IntentWeft"', 'display_name: "IntentWeft"broken"')
        path.write_text(text, encoding="utf-8")
        self.assertTrue(any("Invalid interface metadata" in error for error in checker.check(self.root)))

    def test_duplicate_interface_field_is_rejected(self):
        path = self.root / "skills" / "intentweft" / "agents" / "openai.yaml"
        with path.open("a", encoding="utf-8") as handle:
            handle.write('  display_name: "Duplicate"\n')
        self.assertTrue(any("Invalid interface metadata" in error for error in checker.check(self.root)))

    def test_wrong_interface_mapping_is_rejected(self):
        path = self.root / "skills" / "intentweft" / "agents" / "openai.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("interface:", "wrong_mapping:"), encoding="utf-8")
        self.assertTrue(any("Invalid interface metadata" in error for error in checker.check(self.root)))

    def test_missing_linked_resource_is_rejected(self):
        (self.root / "skills" / "intentweft" / "references" / "review-protocol.md").unlink()
        self.assertTrue(any("Broken local link" in error and "review-protocol.md" in error for error in checker.check(self.root)))

    def test_duplicate_json_key_in_example_is_rejected(self):
        path = self.root / "skills" / "intentweft" / "assets" / "report.example.json"
        text = path.read_text(encoding="utf-8").replace('"schema_version": 1', '"schema_version": 999, "schema_version": 1')
        path.write_text(text, encoding="utf-8")
        self.assertTrue(any("Invalid example report" in error and "duplicate" in error.lower() for error in checker.check(self.root)))

    def test_python_syntax_error_is_rejected(self):
        (self.root / "tests" / "broken.py").write_text("def broken(:\n", encoding="utf-8")
        self.assertTrue(any("Invalid Python source" in error and "broken.py" in error for error in checker.check(self.root)))


if __name__ == "__main__":
    unittest.main()
