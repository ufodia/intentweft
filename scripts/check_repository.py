#!/usr/bin/env python3
"""Check the repository's portable packaging without third-party dependencies."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "intentweft"


def check() -> list[str]:
    errors: list[str] = []
    required = [
        "README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md",
        "docs/INSTALLATION.md", "scripts/install.py", "evals/README.md",
        "evals/RUBRIC.md", "evals/RESULTS.md", ".github/workflows/validate.yml",
        "skills/intentweft/SKILL.md", "skills/intentweft/agents/openai.yaml",
        "skills/intentweft/scripts/evidence.py",
        "skills/intentweft/assets/report.example.json",
    ]
    for relative in required:
        if not (ROOT / relative).is_file():
            errors.append(f"Missing required file: {relative}")
    skill_file = SKILL / "SKILL.md"
    if skill_file.is_file():
        content = skill_file.read_text(encoding="utf-8")
        # This distribution intentionally uses a simple portable YAML subset.
        front = re.match(r'\A---\nname: intentweft\ndescription: ("[^\n]+")\n---\n', content)
        if front is None:
            errors.append("SKILL.md frontmatter must contain name and quoted description only")
        else:
            try:
                description = json.loads(front[1])
                if not isinstance(description, str) or not 1 <= len(description) <= 1024:
                    errors.append("Skill description must contain 1 to 1024 characters")
            except ValueError:
                errors.append("Skill description must use valid JSON-compatible YAML quoting")
        if len(content.splitlines()) > 500:
            errors.append("SKILL.md exceeds the 500-line context budget")
        if "[TODO" in content:
            errors.append("SKILL.md still contains a template placeholder")
    metadata = SKILL / "agents" / "openai.yaml"
    if metadata.is_file():
        text = metadata.read_text(encoding="utf-8")
        for field in ("display_name", "short_description", "default_prompt"):
            match = re.search(rf'^  {field}: "(.+)"$', text, re.M)
            if not match:
                errors.append(f"Missing or unquoted interface field: {field}")
            elif field == "short_description" and not 25 <= len(match[1]) <= 64:
                errors.append("Interface short_description must contain 25 to 64 characters")
            elif field == "default_prompt" and "$intentweft" not in match[1]:
                errors.append("Interface default_prompt must invoke $intentweft")
    for document in ROOT.rglob("*.md"):
        if any(part in {".git", "__pycache__", ".venv"} for part in document.parts):
            continue
        text = document.read_text(encoding="utf-8")
        for link in re.findall(r'(?<!!)\[[^\]]+\]\(([^)\n]+)\)', text):
            destination = link.strip().split(' "', 1)[0].strip("<>")
            if destination.startswith("#") or urlsplit(destination).scheme:
                continue
            target = unquote(destination.split("#", 1)[0])
            if target and not (document.parent / target).exists():
                errors.append(f"Broken local link in {document.relative_to(ROOT)}: {destination}")
    example = SKILL / "assets" / "report.example.json"
    if example.is_file():
        import importlib.util
        helper = SKILL / "scripts" / "evidence.py"
        if helper.is_file():
            spec = importlib.util.spec_from_file_location("intentweft_evidence", helper)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            try:
                module.validate_report(json.loads(example.read_text(encoding="utf-8")), ROOT)
            except (ValueError, OSError) as exc:
                errors.append(f"Invalid example report: {exc}")
    return errors


if __name__ == "__main__":
    failures = check()
    for failure in failures:
        print(f"Error: {failure}", file=sys.stderr)
    if failures:
        raise SystemExit(1)
    print("Portable skill metadata, resources, local links, and example report are valid.")
