"""Regression tests for evidence boundaries, report references, and verdict rules."""

import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "intentweft" / "scripts" / "evidence.py"
SPEC = importlib.util.spec_from_file_location("intentweft_evidence", SCRIPT)
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "policy.md").write_text("Do not upload location.\n", encoding="utf-8")
        self.report = {
            "schema_version": 1,
            "review": {"mode": "review", "scope": "Location upload", "verdict": "ready"},
            "sources": evidence.capture(self.root, ["policy.md"])["sources"],
            "requirements": [{"id": "R1", "text": "Location stays local", "source_ids": ["S1"], "status": "met"}],
            "findings": [], "unknowns": [],
            "checks": [{"id": "C1", "description": "Read upload path", "status": "passed", "source_ids": ["S1"], "detail": "Scope is limited to the supplied fixture."}],
            "next_actions": [],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_snapshot_contains_only_fingerprints(self):
        result = evidence.capture(self.root, ["policy.md"])
        self.assertEqual(result["sources"][0]["id"], "S1")
        self.assertEqual(result["sources"][0]["locator"], "policy.md")
        self.assertNotIn("Do not upload", json.dumps(result))
        self.assertEqual(len(result["sources"][0]["sha256"]), 64)

    def test_snapshot_and_report_cli(self):
        snapshot = self.root / "sources.json"
        report = self.root / "review.json"
        report.write_text(json.dumps(self.report), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(evidence.main(["snapshot", "--root", str(self.root), "--out", str(snapshot), "policy.md"]), 0)
            self.assertEqual(evidence.main(["check", str(report), "--root", str(self.root)]), 0)
        self.assertEqual(json.loads(snapshot.read_text())["sources"], self.report["sources"])

    def test_changed_file_invalidates_report(self):
        (self.root / "policy.md").write_text("Upload location.\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "fingerprint changed"):
            evidence.validate_report(self.report, self.root)

    def test_traversal_and_absolute_paths_rejected(self):
        for locator in ("../policy.md", "folder/../policy.md", str(self.root / "policy.md"), "C:\\secrets.txt", "\\\\server\\share\\secrets", "/etc/passwd", "policy.md:stream"):
            with self.subTest(locator=locator), self.assertRaises(evidence.EvidenceError):
                evidence.capture(self.root, [locator])

    def test_symlink_escape_rejected(self):
        link = self.root / "link.md"
        try:
            link.symlink_to(self.root / "policy.md")
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable on this host")
        with self.assertRaisesRegex(evidence.EvidenceError, "symlink"):
            evidence.capture(self.root, ["link.md"])

    def test_missing_reference(self):
        self.report["requirements"][0]["source_ids"] = ["S99"]
        with self.assertRaisesRegex(evidence.EvidenceError, "unknown reference"):
            evidence.validate_report(self.report, self.root)

    def test_duplicate_ids(self):
        self.report["sources"].append(copy.deepcopy(self.report["sources"][0]))
        with self.assertRaisesRegex(evidence.EvidenceError, "duplicate id"):
            evidence.validate_report(self.report, self.root)

    def test_malformed_top_types(self):
        for value in (None, [], "report", 1):
            with self.subTest(value=value), self.assertRaises(evidence.EvidenceError):
                evidence.validate_report(value, self.root)
        for field in ("sources", "requirements", "findings", "unknowns", "checks", "next_actions"):
            malformed = copy.deepcopy(self.report)
            malformed[field] = {}
            with self.subTest(field=field), self.assertRaises(evidence.EvidenceError):
                evidence.validate_report(malformed, self.root)

    def test_ready_requires_evidence(self):
        self.report["checks"] = []
        with self.assertRaisesRegex(evidence.EvidenceError, "insufficient-evidence"):
            evidence.validate_report(self.report, self.root)

    def test_known_failure_has_priority_over_unknowns(self):
        self.report["requirements"][0]["status"] = "unmet"
        self.report["unknowns"] = [{"id": "U1", "question": "Production setting?", "blocking": True, "next_step": "Inspect config"}]
        self.report["review"]["verdict"] = "needs-action"
        self.assertEqual(evidence.validate_report(self.report, self.root)["verdict"], "needs-action")

    def test_blocking_unknown_prevents_ready(self):
        self.report["unknowns"] = [{"id": "U1", "question": "Production setting?", "blocking": True, "next_step": "Inspect config"}]
        with self.assertRaisesRegex(evidence.EvidenceError, "insufficient-evidence"):
            evidence.validate_report(self.report, self.root)

    def test_high_open_finding_prevents_ready(self):
        self.report["findings"] = [self.finding()]
        with self.assertRaisesRegex(evidence.EvidenceError, "needs-action"):
            evidence.validate_report(self.report, self.root)

    def test_accepted_risk_reported(self):
        finding = self.finding()
        finding["status"] = "accepted"
        self.report["findings"] = [finding]
        self.assertEqual(evidence.validate_report(self.report, self.root)["accepted_risks"], 1)

    def test_failed_check_prevents_ready(self):
        self.report["checks"][0]["status"] = "failed"
        with self.assertRaisesRegex(evidence.EvidenceError, "needs-action"):
            evidence.validate_report(self.report, self.root)

    def test_non_file_source_requires_date(self):
        self.report["sources"].append({"id": "S2", "kind": "statement", "locator": "User instruction"})
        with self.assertRaisesRegex(evidence.EvidenceError, "observed_at"):
            evidence.validate_report(self.report, self.root)
        self.report["sources"][-1]["observed_at"] = "2026-11-13"
        evidence.validate_report(self.report, self.root)

    def test_duplicate_reference_rejected(self):
        self.report["requirements"][0]["source_ids"] = ["S1", "S1"]
        with self.assertRaisesRegex(evidence.EvidenceError, "duplicate reference"):
            evidence.validate_report(self.report, self.root)

    def test_snapshot_no_overwrite_without_force(self):
        output = self.root / "out.json"
        output.write_text("keep me", encoding="utf-8")
        args = ["snapshot", "--root", str(self.root), "--out", str(output), "policy.md"]
        with redirect_stderr(io.StringIO()):
            self.assertEqual(evidence.main(args), 1)
        self.assertEqual(output.read_text(), "keep me")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(evidence.main(args + ["--force"]), 0)

    def test_snapshot_cannot_overwrite_evidence(self):
        output = self.root / "policy.md"
        args = ["snapshot", "--root", str(self.root), "--out", str(output), "--force", "policy.md"]
        with redirect_stderr(io.StringIO()):
            self.assertEqual(evidence.main(args), 1)
        self.assertEqual(output.read_text(), "Do not upload location.\n")

    def test_malformed_json_cli_no_traceback(self):
        report = self.root / "bad.json"
        report.write_text("{broken", encoding="utf-8")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(evidence.main(["check", str(report), "--root", str(self.root)]), 1)
        self.assertIn("Error:", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    @staticmethod
    def finding():
        return {"id": "F1", "title": "Upload risk", "requirement_ids": ["R1"], "source_ids": ["S1"],
                "severity": "high", "confidence": "inferred", "status": "open", "scenario": "Location leaves device",
                "impact": "Promise violated", "action": "Inspect sender", "verification": "Observe outgoing payload"}


if __name__ == "__main__":
    unittest.main()
