#!/usr/bin/env python3
"""Capture explicit file fingerprints and check IntentWeft report structure/freshness.

No network access, content extraction, model calls, or semantic truth checking.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import sys


class EvidenceError(ValueError):
    """A user-correctable evidence or report error."""


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{where}: expected a nonempty string")
    return value


def _obj(value: object, where: str) -> dict:
    if not isinstance(value, dict):
        raise EvidenceError(f"{where}: expected an object")
    return value


def _list(value: object, where: str, *, nonempty: bool = False) -> list:
    if not isinstance(value, list) or (nonempty and not value):
        suffix = "nonempty " if nonempty else ""
        raise EvidenceError(f"{where}: expected a {suffix}list")
    return value


def _choice(value: object, choices: set[str], where: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise EvidenceError(f"{where}: expected one of {', '.join(sorted(choices))}")
    return value


def _date(value: object, where: str) -> None:
    text = _text(value, where)
    try:
        if "T" in text:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
        else:
            date.fromisoformat(text)
    except ValueError as exc:
        raise EvidenceError(f"{where}: expected an ISO date or timestamp") from exc


def project_file(root: Path, locator: str) -> Path:
    """Resolve one portable relative file locator without traversing symlinks."""
    _text(locator, "file locator")
    windows = PureWindowsPath(locator)
    # Check both syntaxes even when running on POSIX; reports are portable.
    if Path(locator).is_absolute() or windows.is_absolute() or windows.drive or windows.root:
        raise EvidenceError(f"file locator must be relative: {locator}")
    normalized = locator.replace("\\", "/")
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts) or ":" in normalized:
        raise EvidenceError(f"file locator contains an unsafe path component: {locator}")
    base = root.resolve(strict=True)
    if not base.is_dir():
        raise EvidenceError(f"project root is not a directory: {root}")
    target = base
    for part in parts:
        target = target / part
        if target.is_symlink() or (hasattr(target, "is_junction") and target.is_junction()):
            raise EvidenceError(f"symlink or junction file locators are unsupported: {locator}")
    resolved = target.resolve(strict=True)
    if not resolved.is_relative_to(base):
        raise EvidenceError(f"file locator escapes project root: {locator}")
    if not resolved.is_file():
        raise EvidenceError(f"file locator is not a regular file: {locator}")
    return resolved


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capture(root: Path, locators: list[str]) -> dict:
    if not locators:
        raise EvidenceError("snapshot requires at least one explicit file locator")
    sources = []
    seen = set()
    for locator in locators:
        path = project_file(root, locator)
        relative = path.relative_to(root.resolve()).as_posix()
        if relative in seen:
            raise EvidenceError(f"duplicate file locator: {locator}")
        seen.add(relative)
        sources.append({"id": f"S{len(sources) + 1}", "kind": "file",
                        "locator": relative, "sha256": fingerprint(path)})
    return {"sources": sources}


def _records(report: dict, name: str, prefix: str, *, nonempty: bool = False) -> dict[str, dict]:
    result = {}
    for index, raw in enumerate(_list(report.get(name), name, nonempty=nonempty)):
        item = _obj(raw, f"{name}[{index}]")
        item_id = _text(item.get("id"), f"{name}[{index}].id")
        if not re.fullmatch(rf"{prefix}[1-9][0-9]*", item_id):
            raise EvidenceError(f"{name}[{index}].id: expected {prefix} followed by a positive integer")
        if item_id in result:
            raise EvidenceError(f"duplicate id: {item_id}")
        result[item_id] = item
    return result


def _refs(item: dict, key: str, known: dict, where: str, *, nonempty: bool = True) -> list[str]:
    refs = _list(item.get(key), f"{where}.{key}", nonempty=nonempty)
    seen = set()
    for ref in refs:
        _text(ref, f"{where}.{key}")
        if ref not in known:
            raise EvidenceError(f"{where}.{key}: unknown reference {ref}")
        if ref in seen:
            raise EvidenceError(f"{where}.{key}: duplicate reference {ref}")
        seen.add(ref)
    return refs


def validate_report(raw: object, root: Path) -> dict:
    if not root.resolve(strict=True).is_dir():
        raise EvidenceError(f"project root is not a directory: {root}")
    report = _obj(raw, "report")
    if type(report.get("schema_version")) is not int or report["schema_version"] != 1:
        raise EvidenceError("schema_version must be integer 1")
    review = _obj(report.get("review"), "review")
    _choice(review.get("mode"), {"preflight", "review", "verify", "handoff"}, "review.mode")
    _text(review.get("scope"), "review.scope")
    verdict = _choice(review.get("verdict"), {"ready", "needs-action", "insufficient-evidence"}, "review.verdict")
    sources = _records(report, "sources", "S", nonempty=True)
    requirements = _records(report, "requirements", "R", nonempty=True)
    findings = _records(report, "findings", "F")
    unknowns = _records(report, "unknowns", "U")
    checks = _records(report, "checks", "C")
    actions = _list(report.get("next_actions"), "next_actions")
    for index, action in enumerate(actions):
        _text(action, f"next_actions[{index}]")

    for source_id, source in sources.items():
        kind = _choice(source.get("kind"), {"file", "statement", "external", "execution"}, f"{source_id}.kind")
        locator = _text(source.get("locator"), f"{source_id}.locator")
        if kind == "file":
            sha = source.get("sha256")
            if not isinstance(sha, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", sha):
                raise EvidenceError(f"{source_id}.sha256: expected 64 hexadecimal characters")
            if fingerprint(project_file(root, locator)) != sha.lower():
                raise EvidenceError(f"{source_id}: file fingerprint changed: {locator}; inspect the change before refreshing evidence")
        else:
            _date(source.get("observed_at"), f"{source_id}.observed_at")

    for requirement_id, requirement in requirements.items():
        _text(requirement.get("text"), f"{requirement_id}.text")
        _choice(requirement.get("status"), {"met", "unmet", "unknown"}, f"{requirement_id}.status")
        _refs(requirement, "source_ids", sources, requirement_id)

    for finding_id, finding in findings.items():
        for field in ("title", "scenario", "impact", "action", "verification"):
            _text(finding.get(field), f"{finding_id}.{field}")
        _refs(finding, "source_ids", sources, finding_id)
        _refs(finding, "requirement_ids", requirements, finding_id)
        _choice(finding.get("severity"), {"critical", "high", "medium", "low"}, f"{finding_id}.severity")
        _choice(finding.get("confidence"), {"confirmed", "inferred", "unknown"}, f"{finding_id}.confidence")
        _choice(finding.get("status"), {"open", "resolved", "accepted"}, f"{finding_id}.status")
    for unknown_id, unknown in unknowns.items():
        _text(unknown.get("question"), f"{unknown_id}.question")
        _text(unknown.get("next_step"), f"{unknown_id}.next_step")
        if type(unknown.get("blocking")) is not bool:
            raise EvidenceError(f"{unknown_id}.blocking: expected a boolean")
    for check_id, check in checks.items():
        _text(check.get("description"), f"{check_id}.description")
        _text(check.get("detail"), f"{check_id}.detail")
        status = _choice(check.get("status"), {"passed", "failed", "not-run"}, f"{check_id}.status")
        _refs(check, "source_ids", sources, check_id, nonempty=status != "not-run")

    known_failure = (any(r["status"] == "unmet" for r in requirements.values())
                     or any(c["status"] == "failed" for c in checks.values())
                     or any(f["status"] == "open" and f["severity"] in {"critical", "high"} for f in findings.values()))
    missing_evidence = (any(r["status"] == "unknown" for r in requirements.values())
                        or any(u["blocking"] for u in unknowns.values())
                        or not any(c["status"] in {"passed", "failed"} for c in checks.values()))
    expected = "needs-action" if known_failure else "insufficient-evidence" if missing_evidence else "ready"
    if verdict != expected:
        raise EvidenceError(f"review.verdict is {verdict}; report states require {expected}")
    return {"verdict": expected, "sources": len(sources), "requirements": len(requirements),
            "findings": len(findings), "accepted_risks": sum(f["status"] == "accepted" for f in findings.values())}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    snapshot = sub.add_parser("snapshot", help="hash explicitly named project files")
    snapshot.add_argument("--root", type=Path, required=True)
    snapshot.add_argument("--out", type=Path, required=True)
    snapshot.add_argument("--force", action="store_true", help="replace an existing regular output file")
    snapshot.add_argument("paths", nargs="+")
    check = sub.add_parser("check", help="validate a report and check local file fingerprints")
    check.add_argument("report", type=Path)
    check.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            result = capture(args.root, args.paths)
            if args.out.is_symlink() or (hasattr(args.out, "is_junction") and args.out.is_junction()):
                raise EvidenceError("snapshot output must not be a symlink or junction")
            # Never truncate an evidence input, even with --force.
            inputs = {project_file(args.root, locator) for locator in args.paths}
            if (args.out.resolve() in inputs
                    or (args.out.exists() and any(args.out.samefile(path) for path in inputs))):
                raise EvidenceError("snapshot output must differ from its evidence inputs")
            mode = "w" if args.force else "x"
            with args.out.open(mode, encoding="utf-8", newline="\n") as handle:
                json.dump(result, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            print(f"Captured {len(result['sources'])} file fingerprint(s): {args.out}")
        else:
            with args.report.open(encoding="utf-8-sig") as handle:
                summary = validate_report(json.load(handle), args.root)
            print(json.dumps(summary, sort_keys=True))
            print("Structure and file freshness checked; semantic truth and completeness were not checked.")
        return 0
    except (EvidenceError, OSError, ValueError, RecursionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
