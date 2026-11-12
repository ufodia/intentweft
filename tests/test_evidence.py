"""Regression tests for evidence boundaries, report references, and verdict rules."""

import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
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

    def test_cli_unicode_output_path_with_ascii_stdout(self):
        output = self.root / "\u03a9-sources.json"
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "snapshot", "--root", str(self.root),
             "--out", str(output), "policy.md"],
            env=dict(os.environ, PYTHONIOENCODING="ascii", PYTHONDONTWRITEBYTECODE="1"),
            capture_output=True, text=True, encoding="ascii", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(r"\u03a9-sources.json", result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["sources"], self.report["sources"])

    def test_changed_file_invalidates_report(self):
        (self.root / "policy.md").write_text("Upload location.\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "fingerprint changed"):
            evidence.validate_report(self.report, self.root)

    def test_traversal_and_absolute_paths_rejected(self):
        for locator in ("../policy.md", "folder/../policy.md", str(self.root / "policy.md"), "C:\\secrets.txt", "\\\\server\\share\\secrets", "/etc/passwd", "policy.md:stream"):
            with self.subTest(locator=locator), self.assertRaises(evidence.EvidenceError):
                evidence.capture(self.root, [locator])

    def test_nonportable_file_components_rejected_before_lookup(self):
        locators = (
            "folder./policy.md", "folder /policy.md", "NUL", "aux.txt",
            "folder/COM1.log", "LPT\u00b2", "NUL .txt", "CONIN$", "CONOUT$",
            'invalid"name.md', "invalid<name.md", "invalid>name.md",
            "invalid|name.md", "invalid?name.md", "invalid*name.md",
            "invalid\x00name.md", "invalid\x1fname.md", "invalid\x7fname.md", "invalid\x85name.md",
        )
        for locator in locators:
            with self.subTest(locator=locator), self.assertRaises(evidence.EvidenceError):
                evidence.capture(self.root, [locator])

    def test_backslash_locator_is_not_reinterpreted_as_a_separator(self):
        folder = self.root / "folder"
        folder.mkdir()
        (folder / "policy.md").write_text("Nested file.\n", encoding="utf-8")
        if os.name != "nt":
            # POSIX permits both distinct names; silently replacing the slash
            # would fingerprint the wrong explicitly named file.
            literal = self.root / "folder\\policy.md"
            literal.write_text("Literal backslash file.\n", encoding="utf-8")
            self.assertNotEqual(literal.read_bytes(), (folder / "policy.md").read_bytes())
        with self.assertRaisesRegex(evidence.EvidenceError, "POSIX '/' separators"):
            evidence.capture(self.root, ["folder\\policy.md"])

    def test_trailing_dot_and_space_file_aliases_rejected(self):
        for suffix in (".", " "):
            locator = "policy.md" + suffix
            alias = self.root / locator
            if os.name == "nt":
                self.assertTrue(alias.samefile(self.root / "policy.md"))
            else:
                alias.write_text("Distinct POSIX file.\n", encoding="utf-8")
                self.assertNotEqual(alias.read_bytes(), (self.root / "policy.md").read_bytes())
            with self.subTest(locator=locator):
                with self.assertRaisesRegex(evidence.EvidenceError, "unsafe path component"):
                    evidence.capture(self.root, [locator])
                self.report["sources"][0]["locator"] = locator
                with self.assertRaisesRegex(evidence.EvidenceError, "unsafe path component"):
                    evidence.validate_report(self.report, self.root)

    def test_unicode_and_embedded_spaces_remain_valid_locators(self):
        folder = self.root / "drafts & notes"
        folder.mkdir()
        (folder / "na\u00efve plan.md").write_text("Synthetic content.\n", encoding="utf-8")
        result = evidence.capture(self.root, ["drafts & notes/na\u00efve plan.md"])
        self.assertEqual(result["sources"][0]["locator"], "drafts & notes/na\u00efve plan.md")

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

    def test_observation_dates_use_a_portable_extended_grammar(self):
        source = {"id": "S2", "kind": "statement", "locator": "Synthetic observation"}
        self.report["sources"].append(source)
        for value in (
            "2024-02-29", "2026-11-13", "2026-11-13T01:02:03Z",
            "2026-11-13T01:02:03.1+05:30", "2026-11-13T01:02:03.123456-04:00",
            "2026-11-13T01:02:03.12Z", "2026-11-13T01:02:03.123Z",
            "2026-11-13T01:02:03.1234Z", "2026-11-13T01:02:03.12345Z",
        ):
            with self.subTest(value=value):
                source["observed_at"] = value
                evidence.validate_report(self.report, self.root)
        for value in (
            "20261113", "2026-W46-5", "2026W465", "2026-317",
            "2026-11-13T01:02:03", "2026-11-13T01:02Z", "2026-11-13t01:02:03Z",
            "2026-11-13T01:02:03.1234567Z", "2026-11-13T01:02:03,5Z",
            "2026-11-13T01:02:03+0530", "2026-11-13T01:02:03+00:00:30",
            "2026-11-13T01:02:03+00:60", "2026-11-13T01:02:03+24:00",
            "2026-11-13T24:00:00Z", "2026-11-13T01:02:60Z", "2026-02-29",
        ):
            with self.subTest(value=value), self.assertRaisesRegex(evidence.EvidenceError, "observed_at"):
                source["observed_at"] = value
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

    def test_output_validation_does_not_require_legacy_is_reserved(self):
        output = self.root / "sources.json"
        with patch.object(evidence.PureWindowsPath, "is_reserved", create=True,
                          side_effect=AssertionError("Legacy pathlib API must not be called")):
            evidence.write_snapshot(output, {"sources": []}, force=False)
            with self.assertRaisesRegex(evidence.EvidenceError, "reserved Windows device"):
                evidence.write_snapshot(self.root / "NUL", {}, force=True)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"sources": []})

    def test_alternate_data_stream_output_rejected_without_orphan_files(self):
        before = set(self.root.iterdir())
        for locator in ("sources.json:stream", "reports:stream/sources.json"):
            for force in (False, True):
                with self.subTest(locator=locator, force=force):
                    with self.assertRaisesRegex(evidence.EvidenceError, "alternate data stream"):
                        evidence.write_snapshot(self.root / locator, {}, force=force)
                    self.assertEqual(set(self.root.iterdir()), before)

    def test_nonportable_output_components_rejected_without_mutation(self):
        output = self.root / "sources.json"
        output.write_text("Keep the original snapshot.\n", encoding="utf-8")
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}
        for locator in (
            "sources.json.", "sources.json ", "folder./sources.json", "folder /sources.json",
            "NUL.json", "reports/COM1.log", "invalid|name.json", 'invalid"name.json',
            "invalid<name.json", "invalid>name.json", "invalid?name.json", "invalid*name.json",
            "invalid\x00name.json", "invalid\x1fname.json", "invalid\x7fname.json", "invalid\x85name.json",
        ):
            for force in (False, True):
                with self.subTest(locator=locator, force=force), self.assertRaises(evidence.EvidenceError):
                    evidence.write_snapshot(self.root / locator, {}, force=force)
                self.assertEqual({path.name: path.read_bytes() for path in self.root.iterdir()}, before)

    def test_output_parent_navigation_remains_supported(self):
        folder = self.root / "reports"
        folder.mkdir()
        output = folder / ".." / "sources.json"
        evidence.write_snapshot(output, {"sources": []}, force=False)
        self.assertEqual(json.loads((self.root / "sources.json").read_text(encoding="utf-8")), {"sources": []})

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
