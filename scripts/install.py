#!/usr/bin/env python3
"""Install the portable IntentWeft skill without downloads or overwrites."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import stat
import sys


SKILL_NAME = "intentweft"
SOURCE = Path(__file__).resolve().parents[1] / "skills" / SKILL_NAME
AGENT_DIRECTORIES = {"codex": ".agents", "claude": ".claude"}


class InstallError(ValueError):
    """An installation cannot safely proceed."""


def validate_metadata(text: str) -> None:
    """Validate this distribution's deliberately small, portable YAML subset."""
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.S)
    if frontmatter is None:
        raise InstallError("SKILL.md must start with YAML frontmatter.")
    fields: dict[str, str] = {}
    for line in frontmatter.group(1).splitlines():
        if not line.strip():
            continue
        field = re.fullmatch(r"([a-z][a-z_]*):[ \t]*(.*)", line)
        if field is None:
            raise InstallError("Unsupported SKILL.md frontmatter; use one name and description field on separate lines.")
        key, value = field.groups()
        if key not in {"name", "description"}:
            raise InstallError(f"Unsupported SKILL.md frontmatter field: {key}.")
        if key in fields:
            raise InstallError(f"Duplicate SKILL.md frontmatter field: {key}.")
        fields[key] = value.strip()
    if fields.get("name") != SKILL_NAME:
        raise InstallError("SKILL.md must declare exactly one plain name: intentweft.")
    raw_description = fields.get("description", "")
    if raw_description.startswith('"'):
        try:
            description = json.loads(raw_description)
        except ValueError as exc:
            raise InstallError("SKILL.md description must use valid JSON-compatible double quoting.") from exc
    else:
        # Supporting a narrow plain-string form keeps installation dependency-free.
        # Reject YAML structures, typed scalars, tags, anchors, and inline comments.
        if (not re.match(r"[A-Za-z]", raw_description)
                or re.search(r":(?:[ \t]|$)|(?:^|[ \t])#", raw_description)
                or re.match(r"[-?:][ \t]", raw_description)
                or raw_description.lower() in {"null", "~", "true", "false", "yes", "no", "on", "off"}
                or re.fullmatch(r"[+-]?(?:[0-9][0-9_]*(?:\.[0-9_]*)?|\.[0-9_]+)(?:[eE][+-]?[0-9]+)?", raw_description)):
            raise InstallError("Unsupported SKILL.md description; use plain English text or JSON-compatible double quoting.")
        description = raw_description
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise InstallError("SKILL.md description must contain 1 to 1024 characters of text.")


def is_link(path: Path) -> bool:
    """Include Windows reparse points on Python versions without is_junction."""
    if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def validate_source(source: Path) -> Path:
    source = source.absolute()
    if is_link(source) or not source.is_dir():
        raise InstallError("The skill source must be a real directory.")
    source = source.resolve(strict=True)
    for entry in source.rglob("*"):
        if is_link(entry):
            raise InstallError(f"Symbolic links are not allowed in the source: {entry}")
        if not (entry.is_dir() or stat.S_ISREG(entry.stat().st_mode)):
            raise InstallError(f"Unsupported source entry: {entry}")
    skill_file = source / "SKILL.md"
    if not skill_file.is_file():
        raise InstallError("The source does not contain SKILL.md.")
    text = skill_file.read_text(encoding="utf-8")
    validate_metadata(text)
    return source


def validate_destination(base: Path, target: Path) -> None:
    try:
        relative = target.relative_to(base)
    except ValueError as exc:
        raise InstallError("The destination must stay inside its installation root.") from exc
    current = base
    for component in relative.parts:
        current = current / component
        if is_link(current):
            raise InstallError(f"Symbolic links are not allowed in destination paths: {current}")
        if current.exists() and not current.is_dir():
            raise InstallError(f"A destination parent is not a directory: {current}")
    if target.exists() or is_link(target):
        raise InstallError(f"The skill is already present; nothing was overwritten: {target}")
    try:
        target.resolve().relative_to(base)
    except ValueError as exc:
        raise InstallError("The destination resolves outside its installation root.") from exc


def create_parents(base: Path, parent: Path, created: list[Path]) -> None:
    current = base
    for component in parent.relative_to(base).parts:
        current = current / component
        if is_link(current):
            raise InstallError(f"A destination parent became a symbolic link: {current}")
        try:
            current.mkdir()
        except FileExistsError:
            if not current.is_dir():
                raise InstallError(f"A destination parent is not a directory: {current}")
        else:
            created.append(current)


def remove_created_target(base: Path, target: Path) -> None:
    """Only remove a newly created skill directory inside the checked root."""
    target.relative_to(base)
    if is_link(target):
        raise InstallError(f"Cannot roll back a destination replaced by a link: {target}")
    target.resolve().relative_to(base)
    if target.exists():
        shutil.rmtree(target)


def install(source: Path, base: Path, agent: str, dry_run: bool = False) -> list[Path]:
    source = validate_source(source)
    base = base.absolute()
    if is_link(base) or not base.is_dir():
        raise InstallError("The installation root must be an existing real directory.")
    base = base.resolve(strict=True)
    agents = list(AGENT_DIRECTORIES) if agent == "both" else [agent]
    if any(name not in AGENT_DIRECTORIES for name in agents):
        raise InstallError("Choose codex, claude, or both.")
    targets = [base / AGENT_DIRECTORIES[name] / "skills" / SKILL_NAME for name in agents]
    # Check every target before creating even the first parent directory.
    for target in targets:
        validate_destination(base, target)
        if target.is_relative_to(source):
            raise InstallError("The destination cannot be inside the skill source.")
    if dry_run:
        return targets

    created_targets: list[Path] = []
    created_parents: list[Path] = []
    try:
        for target in targets:
            create_parents(base, target.parent, created_parents)
            # Atomic mkdir claims an absent destination. Existing skills are never merged.
            target.mkdir()
            created_targets.append(target)
            shutil.copytree(source, target, dirs_exist_ok=True)
    except (OSError, InstallError) as exc:
        rollback_errors = []
        for target in reversed(created_targets):
            try:
                remove_created_target(base, target)
            except (OSError, ValueError) as rollback_exc:
                rollback_errors.append(str(rollback_exc))
        for parent in reversed(created_parents):
            try:
                parent.rmdir()  # Remove only empty parents this operation created.
            except OSError:
                pass
        detail = f" Rollback needs attention: {'; '.join(rollback_errors)}" if rollback_errors else ""
        raise InstallError(f"Installation failed: {exc}.{detail}") from exc
    return targets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=["codex", "claude", "both"], required=True)
    parser.add_argument("--scope", choices=["project", "user"], required=True)
    parser.add_argument("--project", type=Path, help="Existing project directory; required for project scope.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and show destinations without writing.")
    args = parser.parse_args(argv)
    if args.scope == "project" and args.project is None:
        parser.error("--project is required with --scope project")
    if args.scope == "user" and args.project is not None:
        parser.error("--project cannot be combined with --scope user")
    base = args.project if args.scope == "project" else Path.home()
    try:
        targets = install(SOURCE, base, args.agent, args.dry_run)
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    for target in targets:
        print(f"{'Would install' if args.dry_run else 'Installed'} IntentWeft: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
