"""Exercise the actual packaged skill through installed command-line helpers."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InstalledSkillTests(unittest.TestCase):
    def test_distribution_installs_and_helpers_work_in_both_locations(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary).resolve() / "Project with spaces \u03a9"
            project.mkdir()
            (project / "policy.md").write_text("Synthetic policy for installation validation.\n", encoding="utf-8")
            install = subprocess.run(
                [sys.executable, "-B", str(ROOT / "scripts" / "install.py"),
                 "--agent", "both", "--scope", "project", "--project", str(project)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(install.returncode, 0, install.stderr)
            for index, agent in enumerate((".agents", ".claude")):
                with self.subTest(agent=agent):
                    skill = project / agent / "skills" / "intentweft"
                    for resource in ("SKILL.md", "agents/openai.yaml", "references/report-format.md", "assets/review-template.md"):
                        self.assertTrue((skill / resource).is_file(), resource)
                    self.assertFalse(any(path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"} for path in skill.rglob("*")))
                    helper = skill / "scripts" / "evidence.py"
                    snapshot = project / f"sources-{index}.json"
                    captured = subprocess.run(
                        [sys.executable, "-B", str(helper), "snapshot", "--root", str(project), "--out", str(snapshot), "policy.md"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                    )
                    self.assertEqual(captured.returncode, 0, captured.stderr)
                    self.assertEqual(json.loads(snapshot.read_text(encoding="utf-8"))["sources"][0]["locator"], "policy.md")
                    checked = subprocess.run(
                        [sys.executable, "-B", str(helper), "check", str(skill / "assets" / "report.example.json"), "--root", str(project)],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                    )
                    self.assertEqual(checked.returncode, 0, checked.stderr)
                    self.assertEqual(json.loads(checked.stdout.splitlines()[0])["verdict"], "insufficient-evidence")


if __name__ == "__main__":
    unittest.main()
