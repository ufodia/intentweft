"""Exercise installer boundaries using disposable project directories only."""

import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install.py"
SPEC = importlib.util.spec_from_file_location("intentweft_install", SCRIPT)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # Windows temp paths may use short aliases. Match the installer's canonical paths
        # so link mocks exercise the intended boundary instead of missing the target.
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "SKILL.md").write_text(
            "---\nname: intentweft\ndescription: Review project evidence.\n---\n\n# IntentWeft\n",
            encoding="utf-8",
        )
        (self.source / "references").mkdir()
        (self.source / "references" / "protocol.md").write_text("Evidence protocol.\n", encoding="utf-8")
        self.project = self.root / "project"
        self.project.mkdir()

    def symlink(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable in this environment.")

    def test_both_copies_complete_skill(self):
        targets = installer.install(self.source, self.project, "both")
        self.assertEqual(len(targets), 2)
        for target in targets:
            self.assertEqual((target / "SKILL.md").read_bytes(), (self.source / "SKILL.md").read_bytes())
            self.assertEqual((target / "references" / "protocol.md").read_bytes(),
                             (self.source / "references" / "protocol.md").read_bytes())
        self.assertTrue((self.project / ".agents" / "skills" / "intentweft").is_dir())
        self.assertTrue((self.project / ".claude" / "skills" / "intentweft").is_dir())

    def test_dry_run_has_no_side_effects(self):
        targets = installer.install(self.source, self.project, "both", dry_run=True)
        self.assertEqual(len(targets), 2)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_existing_second_target_prevents_all_writes(self):
        target = self.project / ".claude" / "skills" / "intentweft"
        target.mkdir(parents=True)
        marker = target / "local.txt"
        marker.write_text("Keep this.", encoding="utf-8")
        with self.assertRaises(installer.InstallError):
            installer.install(self.source, self.project, "both")
        self.assertFalse((self.project / ".agents").exists())
        self.assertEqual(marker.read_text(encoding="utf-8"), "Keep this.")

    def test_cli_requires_project_for_project_scope(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            installer.main(["--agent", "codex", "--scope", "project"])
        self.assertEqual(error.exception.code, 2)

    def test_cli_rejects_project_for_user_scope(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            installer.main(["--agent", "codex", "--scope", "user", "--project", str(self.project)])
        self.assertEqual(error.exception.code, 2)

    def test_invalid_skill_name_is_rejected(self):
        (self.source / "SKILL.md").write_text("---\nname: other\n---\n", encoding="utf-8")
        with self.assertRaises(installer.InstallError):
            installer.install(self.source, self.project, "codex")
        self.assertEqual(list(self.project.iterdir()), [])

    def test_invalid_metadata_is_rejected_before_any_installation(self):
        invalid = [
            "name: intentweft",
            "name: intentweft\ndescription:",
            'name: intentweft\ndescription: "   "',
            "name: intentweft\ndescription: Review.\ndescription: Again.",
            "name: intentweft\nname: intentweft\ndescription: Review.",
            "name:\nintentweft\ndescription: Review.",
            'name: "intentweft\ndescription: Review.',
            'name: intentweft\ndescription: "Unfinished',
            "name: intentweft\ndescription: 'Unfinished",
            "name: intentweft\ndescription: true",
            "name: intentweft\ndescription: 42",
            "name: intentweft\ndescription: 2026-11-13",
            "name: intentweft\ndescription: 0x10",
            "name: intentweft\ndescription: .nan",
            "name: intentweft\ndescription: [Review]",
            "name: intentweft\ndescription: *missing_anchor",
            "name: intentweft\ndescription: Review: evidence",
            "name: intentweft\ndescription: Review. # comment",
            "name: intentweft\ndescription: Review.\nmetadata: value",
            'name: intentweft\ndescription: "' + "A" * 1025 + '"',
        ]
        for frontmatter in invalid:
            with self.subTest(frontmatter=frontmatter):
                (self.source / "SKILL.md").write_text("---\n" + frontmatter + "\n---\n", encoding="utf-8")
                with self.assertRaises(installer.InstallError):
                    installer.install(self.source, self.project, "both")
                self.assertEqual(list(self.project.iterdir()), [])

    def test_json_quoted_description_is_supported(self):
        (self.source / "SKILL.md").write_text(
            '---\nname: intentweft\ndescription: "Review evidence: compare \\"before\\" and after."\n---\n',
            encoding="utf-8",
        )
        targets = installer.install(self.source, self.project, "both", dry_run=True)
        self.assertEqual(len(targets), 2)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_nonregular_skill_source_is_rejected(self):
        (self.source / "SKILL.md").unlink()
        (self.source / "SKILL.md").mkdir()
        with self.assertRaisesRegex(installer.InstallError, "does not contain SKILL.md"):
            installer.install(self.source, self.project, "both")
        self.assertEqual(list(self.project.iterdir()), [])

    def test_nested_source_symlink_is_rejected(self):
        outside = self.root / "outside.txt"
        outside.write_text("Private data.", encoding="utf-8")
        self.symlink(self.source / "linked.txt", outside)
        with self.assertRaises(installer.InstallError):
            installer.install(self.source, self.project, "codex")
        self.assertEqual(list(self.project.iterdir()), [])

    def test_source_directory_symlink_is_rejected(self):
        source_link = self.root / "source-link"
        self.symlink(source_link, self.source, directory=True)
        with self.assertRaises(installer.InstallError):
            installer.install(source_link, self.project, "codex")

    def test_destination_parent_symlink_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.symlink(self.project / ".agents", outside, directory=True)
        with self.assertRaises(installer.InstallError):
            installer.install(self.source, self.project, "codex")
        self.assertEqual(list(outside.iterdir()), [])

    def test_reported_destination_link_is_rejected_without_link_privileges(self):
        dangerous = self.project / ".agents"
        real_is_link = installer.is_link
        with patch.object(installer, "is_link", side_effect=lambda path: path == dangerous or real_is_link(path)):
            with self.assertRaisesRegex(installer.InstallError, "Symbolic links are not allowed in destination paths"):
                installer.install(self.source, self.project, "codex")
        self.assertEqual(list(self.project.iterdir()), [])

    def test_reported_source_link_is_rejected_without_link_privileges(self):
        dangerous = self.source / "references" / "protocol.md"
        real_is_link = installer.is_link
        with patch.object(installer, "is_link", side_effect=lambda path: path == dangerous or real_is_link(path)):
            with self.assertRaisesRegex(installer.InstallError, "Symbolic links are not allowed in the source"):
                installer.install(self.source, self.project, "codex")
        self.assertEqual(list(self.project.iterdir()), [])

    def test_broken_destination_symlink_is_rejected(self):
        parent = self.project / ".agents" / "skills"
        parent.mkdir(parents=True)
        self.symlink(parent / "intentweft", self.root / "missing", directory=True)
        with self.assertRaises(installer.InstallError):
            installer.install(self.source, self.project, "codex")

    def test_installation_inside_source_is_rejected(self):
        with self.assertRaises(installer.InstallError):
            installer.install(self.source, self.source, "codex")
        self.assertFalse((self.source / ".agents").exists())

    def test_copy_failure_rolls_back_only_new_paths(self):
        preexisting = self.project / ".agents"
        preexisting.mkdir()
        marker = preexisting / "keep.txt"
        marker.write_text("Keep this.", encoding="utf-8")
        real_copytree = installer.shutil.copytree

        def fail_second(source, destination, *args, **kwargs):
            if Path(destination).parts[-3] == ".claude":
                (Path(destination) / "partial.txt").write_text("partial", encoding="utf-8")
                raise OSError("Simulated copy failure")
            return real_copytree(source, destination, *args, **kwargs)

        with patch.object(installer.shutil, "copytree", side_effect=fail_second):
            with self.assertRaises(installer.InstallError):
                installer.install(self.source, self.project, "both")
        self.assertEqual(list(preexisting.iterdir()), [marker])
        self.assertFalse((self.project / ".claude").exists())


if __name__ == "__main__":
    unittest.main()
