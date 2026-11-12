# IntentWeft

**Keep project intent woven into every AI change.**

A portable skill for **Codex and Claude Code** that connects project requirements to evidence, realistic failure scenarios, practical corrections, and honest verification results.

An AI change can look correct while violating a promise buried in a product brief, a constraint in a decision record, or a behavior another component depends on. IntentWeft gives the agent a repeatable way to find those mismatches and explain what to do next.

> **Example:** A location app promises to keep precise coordinates on the device. A new analytics event sends them to a server. IntentWeft traces the promise to the payload, describes the permission-granted scenario, proposes a correction, and specifies how to verify the outgoing request.

The name combines **intent** with **weft**, the thread that binds a woven structure together.

## What you get

- A concise [portable skill](skills/intentweft/SKILL.md) with four modes: preflight, review, verify, and handoff.
- A review method that distinguishes observed facts, inferences, requirements, and unknowns.
- Source-linked findings with a trigger, impact, correction, and verification step.
- A [human report template](skills/intentweft/assets/review-template.md) and an optional [structured report](skills/intentweft/assets/report.example.json).
- A Python helper that fingerprints explicitly selected files and checks report structure, cross-references, verdict consistency, and file freshness.
- A local installer for Codex, Claude Code, or both. No API key, account, server, or third-party Python package is required by the bundled tools.
- Synthetic examples, evaluation fixtures, automated helper tests, and a CI workflow.

## Install

Clone the repository and use Python 3.10 or later:

```bash
git clone https://github.com/ufodia/intentweft.git
cd intentweft
```

Install into a project for both agents:

```bash
python scripts/install.py --agent both --scope project --project /absolute/path/to/your-project --dry-run
python scripts/install.py --agent both --scope project --project /absolute/path/to/your-project
```

On Windows, use a quoted Windows path such as `"C:\Projects\my-app"`. Use `python3` instead of `python` if that is your Python command.

To install for only one agent, use `--agent codex` or `--agent claude`. For your user account across projects:

```bash
python scripts/install.py --agent both --scope user --dry-run
python scripts/install.py --agent both --scope user
```

The installer copies the same skill source to these supported locations:

| Agent | Project installation | User installation |
| --- | --- | --- |
| Codex | `<project>/.agents/skills/intentweft/` | `~/.agents/skills/intentweft/` |
| Claude Code | `<project>/.claude/skills/intentweft/` | `~/.claude/skills/intentweft/` |

Existing skill folders are protected. The installer refuses to overwrite them. See [installation and updates](docs/INSTALLATION.md) for manual copying, removal, and compatibility notes.

## Use it

In Codex:

```text
Use $intentweft to review this branch against the product requirements.
Find contradictions, trace each material finding to evidence, and give
me the smallest practical fixes. Keep the review limited to this change.
```

In Claude Code:

```text
/intentweft Review this branch against the product requirements.
Trace material findings to evidence and give me the smallest practical fixes.
```

You can also request a mode explicitly:

| Situation | Example request |
| --- | --- |
| Before implementation | "Preflight this account-deletion plan against our retention promises and current storage design." |
| Conflicting instructions | "Resolve the conflicts between this specification, the latest decision, and the implementation. Show unresolved ambiguity." |
| After a fix | "Verify whether F2 is resolved. Reinspect changed sources and report which checks actually ran." |
| Switching agents | "Prepare an IntentWeft handoff with the goal, current revision, evidence anchors, active decisions, unknowns, and next step." |
| Evidence-heavy documents | "Review this summary for claims that the supplied documents do not support." |

For a small task the skill returns a short inline review. Durable files are useful for larger changes and handoffs; it does not create a project bureaucracy for every edit.

## How it works

1. Establish the intended outcome, scope, current revision, and authorized actions.
2. Read relevant requirements and implementation evidence; identify stale or conflicting sources.
3. Turn the outcome into observable acceptance criteria.
4. Trace realistic failure scenarios and check evidence that could disprove a suspected problem.
5. Propose or implement authorized corrections, then record actual verification.
6. Deliver a bounded verdict, remaining unknowns, and executable next actions.

Every material finding follows this connection:

**Requirement → evidence → trigger → consequence → correction → verification.**

The useful combination is intent preservation, evidence provenance, contradiction handling, and verification honesty. IntentWeft is a workflow skill, with small deterministic helpers for bookkeeping. Model reasoning remains responsible for interpreting the project.

## What a result looks like

```text
Verdict: Needs action
Scope: Location analytics change; static inspection only

F1 — Analytics payload includes precise coordinates
Requirement: R1, product-brief.md, "Data promise"
Evidence: analytics.ts, trackMapOpen(), outgoing latitude/longitude fields
Trigger: trackMapOpen() is called with a device position
Impact: The analytics path contradicts the documented storage promise
Action: Remove precise coordinates from the event and review downstream fields
Verification: Inspect a captured outgoing event after the fix
Status: Not run; static evidence establishes the payload, not production traffic
```

Read the complete [worked example](examples/location-privacy/REVIEW.md) or try the [evaluation fixtures](evals/README.md).

## Optional evidence helper

Fingerprint selected files before writing a durable JSON report:

```bash
python skills/intentweft/scripts/evidence.py snapshot --root /path/to/project --out sources.json product-brief.md src/analytics.ts
```

Copy the generated source entries into your report and retain its other required fields. Then check it:

```bash
python skills/intentweft/scripts/evidence.py check report.json --root /path/to/project
```

The helper reads only named files and performs no network requests. It stores paths and hashes, not file contents. A changed file hash makes the report stale. It does not detect unlisted changes, authenticate evidence, evaluate legal compliance, run project tests, or prove semantic correctness. See the [report contract](skills/intentweft/references/report-format.md).

## Boundaries

IntentWeft follows the host's permissions and project instructions. A review request does not authorize deployment, publication, or changes to live systems. The skill works with the files and tools its host makes available; it does not share hidden memory between Codex and Claude.

`Ready` always means **ready within the stated scope and evidence**. Missing evidence stays visible. Accepted risks remain disclosed. The skill cannot guarantee detection of every problem or certify security, legal outcomes, or correctness.

The portable source uses common `SKILL.md` frontmatter and no required vendor-specific tool calls. `agents/openai.yaml` provides optional Codex interface metadata. This repository documents local Codex and Claude Code installation; account-level ChatGPT, Claude.ai, and cloud-session packaging can have different installation requirements.

## Development and evaluation

```bash
python scripts/check_repository.py
python -m unittest discover -s tests -v
```

CI runs structural checks and helper tests on Windows and Linux. These checks validate packaging and code behavior; they do not measure model review quality. [Evaluation guidance](evals/README.md) explains how to run fresh agent sessions against the synthetic cases without leaking expected answers.

See [contributing](CONTRIBUTING.md), [security reporting](SECURITY.md), and the [MIT license](LICENSE).

## Official format references

- [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code: Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [Agent Skills specification](https://agentskills.io/specification)

Installation locations and formats were checked on November 13, 2026. Host versions and organization policies can affect availability.
