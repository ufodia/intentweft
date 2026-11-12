"""Regression tests for evidence boundaries, report references, and verdict rules."""

import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "intentweft" / "scripts" / "evidence.py"
SPEC = importlib.util.spec_from_file_location("intentweft_evidence", SCRIPT)
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        # Match resolved helper paths when Windows exposes a short temporary-path alias.
        self.root = Path(self.temp.name).resolve()
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
        self.report["sources"].append({"id": "S2", "kind": "statement", "locator": "Authorized owner accepted F1 for this release", "observed_at": "2026-11-13"})
        finding["acceptance_source_ids"] = ["S2"]
        self.report["findings"] = [finding]
        self.assertEqual(evidence.validate_report(self.report, self.root)["accepted_risks"], 1)

    def test_accepted_risk_requires_decision_source(self):
        finding = self.finding()
        finding["status"] = "accepted"
        self.report["findings"] = [finding]
        for references in (None, [], ["S99"]):
            with self.subTest(references=references):
                if references is None:
                    finding.pop("acceptance_source_ids", None)
                else:
                    finding["acceptance_source_ids"] = references
                with self.assertRaisesRegex(evidence.EvidenceError, "acceptance_source_ids"):
                    evidence.validate_report(self.report, self.root)

    def test_execution_source_cannot_accept_risk(self):
        finding = self.finding()
        finding.update(status="accepted", acceptance_source_ids=["S2"])
        self.report["sources"].append({"id": "S2", "kind": "execution", "locator": "test command passed", "observed_at": "2026-11-13"})
        self.report["findings"] = [finding]
        with self.assertRaisesRegex(evidence.EvidenceError, "cannot authorize acceptance"):
            evidence.validate_report(self.report, self.root)

    def test_unknown_open_finding_prevents_ready(self):
        finding = self.finding()
        finding["confidence"] = "unknown"
        self.report["findings"] = [finding]
        with self.assertRaisesRegex(evidence.EvidenceError, "insufficient-evidence"):
            evidence.validate_report(self.report, self.root)
        self.report["review"]["verdict"] = "insufficient-evidence"
        self.assertEqual(evidence.validate_report(self.report, self.root)["verdict"], "insufficient-evidence")
        self.report["requirements"][0]["status"] = "unmet"
        self.report["review"]["verdict"] = "needs-action"
        self.assertEqual(evidence.validate_report(self.report, self.root)["verdict"], "needs-action")

    def test_required_unrun_check_prevents_ready(self):
        self.report["checks"].append({"id": "C2", "description": "Run integration check", "status": "not-run", "source_ids": [], "detail": "Environment unavailable"})
        with self.assertRaisesRegex(evidence.EvidenceError, "insufficient-evidence"):
            evidence.validate_report(self.report, self.root)
        self.report["checks"][-1]["required"] = False
        self.assertEqual(evidence.validate_report(self.report, self.root)["verdict"], "ready")

    def test_check_required_flag_must_be_boolean(self):
        for value in (None, "false", 0, 1, []):
            with self.subTest(value=value):
                self.report["checks"][0]["required"] = value
                with self.assertRaisesRegex(evidence.EvidenceError, "required: expected a boolean"):
                    evidence.validate_report(self.report, self.root)

    def test_optional_failed_check_still_requires_action(self):
        self.report["checks"][0].update(required=False, status="failed")
        self.report["review"]["verdict"] = "needs-action"
        self.assertEqual(evidence.validate_report(self.report, self.root)["verdict"], "needs-action")

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

    def test_duplicate_json_keys_rejected_at_every_depth(self):
        document = json.dumps(self.report)
        cases = [
            document.replace('"schema_version": 1', '"schema_version": 999, "schema_version": 1', 1),
            document.replace('"status": "met"', '"status": "unmet", "status": "met"', 1),
        ]
        report = self.root / "duplicate.json"
        for raw in cases:
            with self.subTest(raw=raw):
                report.write_text(raw, encoding="utf-8")
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    self.assertEqual(evidence.main(["check", str(report), "--root", str(self.root)]), 1)
                self.assertIn("duplicate JSON object key", stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_nonstandard_json_constants_rejected(self):
        report = self.root / "constants.json"
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                document = json.dumps(self.report)[:-1] + ', "extra": ' + constant + '}'
                report.write_text(document, encoding="utf-8")
                with self.assertRaisesRegex(evidence.EvidenceError, "nonstandard JSON constant"):
                    evidence.load_report(report)

    def test_failed_force_write_preserves_existing_snapshot(self):
        output = self.root / "sources.json"
        output.write_text("previous valid snapshot", encoding="utf-8")
        args = ["snapshot", "--root", str(self.root), "--out", str(output), "--force", "policy.md"]
        with patch.object(evidence.os, "fsync", side_effect=OSError("Simulated storage failure")), redirect_stderr(io.StringIO()):
            self.assertEqual(evidence.main(args), 1)
        self.assertEqual(output.read_text(encoding="utf-8"), "previous valid snapshot")
        self.assertEqual(list(self.root.glob(".sources.json.*.tmp")), [])

    def test_failed_new_snapshot_write_removes_partial_file(self):
        output = self.root / "sources.json"
        args = ["snapshot", "--root", str(self.root), "--out", str(output), "policy.md"]
        with patch.object(evidence.os, "fsync", side_effect=OSError("Simulated storage failure")), redirect_stderr(io.StringIO()):
            self.assertEqual(evidence.main(args), 1)
        self.assertFalse(output.exists())

    def test_failed_atomic_replace_preserves_existing_snapshot(self):
        output = self.root / "sources.json"
        output.write_text("previous valid snapshot", encoding="utf-8")
        args = ["snapshot", "--root", str(self.root), "--out", str(output), "--force", "policy.md"]
        with patch.object(evidence.os, "replace", side_effect=OSError("Simulated replacement failure")), redirect_stderr(io.StringIO()):
            self.assertEqual(evidence.main(args), 1)
        self.assertEqual(output.read_text(encoding="utf-8"), "previous valid snapshot")
        self.assertEqual(list(self.root.glob(".sources.json.*.tmp")), [])

    def test_output_directory_and_special_file_rejected(self):
        with self.assertRaisesRegex(evidence.EvidenceError, "regular file"):
            evidence.write_snapshot(self.root, {}, force=True)
        output = self.root / "sources.json"
        output.write_text("keep", encoding="utf-8")
        # Simulate a FIFO/device mode without creating a host special file.
        real_stat = Path.stat
        def special_mode(path, *args, **kwargs):
            result = real_stat(path, *args, **kwargs)
            return SimpleNamespace(st_mode=evidence.stat.S_IFIFO) if path == output else result
        with patch.object(Path, "stat", special_mode), self.assertRaisesRegex(evidence.EvidenceError, "regular file"):
            evidence.write_snapshot(output, {}, force=True)
        self.assertEqual(output.read_text(encoding="utf-8"), "keep")

    def test_reserved_device_output_rejected(self):
        with self.assertRaisesRegex(evidence.EvidenceError, "reserved Windows device"):
            evidence.write_snapshot(self.root / "NUL", {}, force=True)

    def test_reparse_detection_without_is_junction(self):
        target = self.root / "policy.md"
        real_lstat = Path.lstat
        def reparse_stat(path, *args, **kwargs):
            result = real_lstat(path, *args, **kwargs)
            return SimpleNamespace(st_file_attributes=0x400) if path == target else result
        with patch.object(Path, "is_symlink", return_value=False), \
                patch.object(Path, "is_junction", return_value=False, create=True), \
                patch.object(Path, "lstat", reparse_stat), \
                patch.object(evidence.stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400, create=True):
            self.assertTrue(evidence.is_link(target))
            with self.assertRaisesRegex(evidence.EvidenceError, "symlink or junction"):
                evidence.capture(self.root, ["policy.md"])

    def test_output_reparse_ancestor_rejected(self):
        ancestor = self.root / "reports"
        ancestor.mkdir()
        real_is_link = evidence.is_link
        with patch.object(evidence, "is_link", side_effect=lambda path: path == ancestor or real_is_link(path)):
            with self.assertRaisesRegex(evidence.EvidenceError, "paths must not contain"):
                evidence.write_snapshot(ancestor / "sources.json", {}, force=True)
        self.assertEqual(list(ancestor.iterdir()), [])

    @staticmethod
    def finding():
        return {"id": "F1", "title": "Upload risk", "requirement_ids": ["R1"], "source_ids": ["S1"],
                "severity": "high", "confidence": "inferred", "status": "open", "scenario": "Location leaves device",
                "impact": "Promise violated", "action": "Inspect sender", "verification": "Observe outgoing payload"}


if __name__ == "__main__":
    unittest.main()
