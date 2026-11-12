#!/usr/bin/env python3
"""Check the repository's portable packaging without third-party dependencies."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load repository helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def interface_values(text: str) -> dict[str, str]:
    """Read only the interface mapping used by this distribution."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != "interface:":
        raise ValueError("Expected one interface mapping")
    values: dict[str, str] = {}
    allowed = {"display_name", "short_description", "default_prompt"}
    for line in lines[1:]:
        match = re.fullmatch(r"  ([a-z_]+): (.+)", line)
        if match is None or match[1] not in allowed or match[1] in values:
            raise ValueError("Unsupported or duplicate interface field")
        value = json.loads(match[2])
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Expected a nonempty quoted interface string: {match[1]}")
        values[match[1]] = value
    if values.keys() != allowed:
        raise ValueError("Interface must declare display_name, short_description, and default_prompt")
    return values


def check(root: Path = ROOT) -> list[str]:
    root = root.resolve()
    skill = root / "skills" / "intentweft"
    errors: list[str] = []

    def read_text(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"Cannot read UTF-8 text in {path.relative_to(root)}: {exc}")
            return None
    required = [
        "README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md",
        "docs/INSTALLATION.md", "scripts/install.py", "evals/README.md",
        "evals/RUBRIC.md", "evals/RESULTS.md", ".github/workflows/validate.yml",
        "skills/intentweft/SKILL.md", "skills/intentweft/agents/openai.yaml",
        "skills/intentweft/scripts/evidence.py",
        "skills/intentweft/assets/report.example.json",
    ]
    for relative in required:
        if not (root / relative).is_file():
            errors.append(f"Missing required file: {relative}")
    skill_file = skill / "SKILL.md"
    if skill_file.is_file():
        content = read_text(skill_file)
    else:
        content = None
    if content is not None:
        # Use the installer's exact subset rather than a divergent second parser.
        installer_path = root / "scripts" / "install.py"
        if installer_path.is_file():
            try:
                load_module(installer_path, "intentweft_install_check").validate_metadata(content)
            except (ValueError, OSError, SyntaxError, RecursionError) as exc:
                errors.append(f"Invalid skill metadata: {exc}")
        if len(content.splitlines()) > 500:
            errors.append("SKILL.md exceeds the 500-line context budget")
        if "[TODO" in content:
            errors.append("SKILL.md still contains a template placeholder")
    metadata = skill / "agents" / "openai.yaml"
    if metadata.is_file():
        try:
            metadata_text = read_text(metadata)
            if metadata_text is not None:
                values = interface_values(metadata_text)
                if not 25 <= len(values["short_description"]) <= 64:
                    errors.append("Interface short_description must contain 25 to 64 characters")
                if not re.search(r"\$intentweft(?![A-Za-z0-9_-])", values["default_prompt"]):
                    errors.append("Interface default_prompt must invoke $intentweft")
        except ValueError as exc:
            errors.append(f"Invalid interface metadata: {exc}")
    for document in root.rglob("*.md"):
        if any(part in {".git", "__pycache__", ".venv"} for part in document.parts):
            continue
        text = read_text(document)
        if text is None:
            continue
        for link in re.findall(r'(?<!!)\[[^\]]+\]\(([^)\n]+)\)', text):
            destination = link.strip().split(' "', 1)[0].strip("<>")
            if destination.startswith("#") or urlsplit(destination).scheme:
                continue
            target = unquote(destination.split("#", 1)[0])
            if target and not (document.parent / target).exists():
                errors.append(f"Broken local link in {document.relative_to(root)}: {destination}")
    for source in root.rglob("*.py"):
        if any(part in {".git", "__pycache__", ".venv"} for part in source.parts):
            continue
        try:
            compile(source.read_text(encoding="utf-8"), str(source), "exec")
        except (SyntaxError, UnicodeError, OSError) as exc:
            errors.append(f"Invalid Python source in {source.relative_to(root)}: {exc}")
    example = skill / "assets" / "report.example.json"
    if example.is_file():
        helper = skill / "scripts" / "evidence.py"
        if helper.is_file():
            try:
                module = load_module(helper, "intentweft_evidence_check")
                module.validate_report(module.load_report(example), root)
            except (ValueError, OSError, SyntaxError, RecursionError) as exc:
                errors.append(f"Invalid example report: {exc}")
    return errors


if __name__ == "__main__":
    failures = check()
    for failure in failures:
        print(f"Error: {failure}", file=sys.stderr)
    if failures:
        raise SystemExit(1)
    print("Portable skill metadata, resources, local links, and example report are valid.")
