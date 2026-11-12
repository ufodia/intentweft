---
name: intentweft
description: "Review changes against project intent, constraints, and evidence. Use for preflight reviews, conflicting requirements, code/document drift, unsupported claims, release decisions, or Codex/Claude handoffs. Produce source-linked findings, actionable fixes, and explicit verification limits."
---

# IntentWeft

Connect each material project requirement to evidence, a failure scenario, and a practical next action. Treat a review as a bounded assessment of the inspected material.

## 1. Establish the task

Identify the requested outcome, working directory, relevant revision or diff, and authorized actions. Choose the smallest useful mode:

| Mode | Work |
| --- | --- |
| Preflight | Inspect a proposed change before implementation; identify constraints and likely failure paths. |
| Review | Compare existing code, documents, or a diff against the intended outcome. |
| Verify | Revisit findings after a fix; collect fresh evidence for the affected behavior. |
| Handoff | Prepare a concise, source-linked state another agent can reconstruct. |

Default to review when the user asks for an assessment. Implement fixes only when requested or already authorized. Respect the host's permissions, project instructions, and the user's scope. Keep low-impact tasks short; use a focused inline response unless a durable report is useful or requested.

## 2. Reconstruct the evidence

Start with the current user request and applicable project instructions. Read only the relevant requirements, implementation paths, configuration, tests, and decision records. Follow a failing path far enough to establish its cause. Avoid broad unrelated audits.

Read [evidence-rules.md](references/evidence-rules.md) for authority conflicts, source anchors, freshness, and trust boundaries. Preserve these distinctions:

- **Requirement:** an intended outcome or constraint, with an identifiable origin.
- **Observed fact:** something supported by the inspected source or execution.
- **Inference:** a reasoned consequence whose conditions must be stated.
- **Unknown:** missing information plus the smallest step that would resolve it.

When requirements conflict, show both sources. Apply a clear, authorized supersession; retain the history in the handoff. Treat an unresolved material conflict as an unknown rather than choosing silently. Never treat current implementation as authority for intended behavior.

Record source locations precisely: file plus lines or symbol and revision, document page/section, dated user statement, official URL with access date, or command with result and working directory. Re-read stale source material; a previous agent's summary is a pointer to evidence, not evidence that the work succeeded.

## 3. Build a small review contract

Translate the outcome into observable requirements. Assign stable IDs such as `R1`, `S1`, and `F1` only when they improve traceability. Define what would satisfy each requirement and mark it `met`, `unmet`, or `unknown`.

Include only relevant constraints: permissions, data lifecycle, payments, compatibility, operations, scheduling, or substantiation of claims. Do not invent regulations, user preferences, or risk categories to fill a checklist. Verify current official sources when a conclusion depends on changing external rules; if access is unavailable, mark that conclusion unverified.

## 4. Trace concrete failure scenarios

For every material finding, connect:

`requirement → evidence → trigger → consequence → correction → verification`

Read [review-protocol.md](references/review-protocol.md) for severity, confidence, prioritization, and mode-specific behavior. Try the smallest realistic counterexample: another account, a retry, a denied permission, an offline transition, an expired date, a changed premise, or an unsupported statement. Select scenarios from the actual task.

Check disconfirming evidence before escalating a suspicion. Look for callers, middleware, transaction boundaries, deployment settings, and explicit exceptions that could invalidate it. Keep severity separate from confidence. Report a plausible but unestablished risk as an inference or unknown; do not invent an exploit, legal conclusion, or observed failure.

## 5. Resolve and verify within scope

If implementation is authorized, make the smallest coherent change that satisfies the requirement. Preserve unrelated user work. Run checks appropriate to the change when permitted; prefer an existing relevant check or a focused reproduction. Never claim an execution that did not occur.

For each check record `passed`, `failed`, or `not-run`, whether it is required to support the conclusion, the evidence, and the practical limit. Treat checks as required by default. If a required check cannot run, mark the affected requirement `unknown`; another passing check cannot substitute for missing evidence. Use an optional check only when its omission does not affect the scoped conclusion, and explain that limit. Separate static inspection from runtime behavior. A command exiting successfully supports only what the command actually checked. Reopen a finding when the evidence for its resolution becomes stale.

Use the bundled helper when a durable report needs file freshness and structural checks:

```text
python <skill-dir>/scripts/evidence.py snapshot --root <project> --out <sources.json> <relative-file> ...
python <skill-dir>/scripts/evidence.py check <report.json> --root <project>
```

Inspect the script before running it if required by the host. Supply explicitly selected files within the authorized project scope; do not scan unrelated private directories or credential files. The helper hashes files and validates report consistency. It does not establish that claims are true, tests are sufficient, or the system is secure. See [report-format.md](references/report-format.md) and [report.example.json](assets/report.example.json).

## 6. Deliver a decision the user can use

Lead with one bounded verdict:

- **Ready within scope:** all reviewed requirements are supported, required verification ran, and no open high/critical finding, open finding with unknown confidence, or blocking unknown remains. Disclose accepted risks and untested boundaries.
- **Needs action:** evidence shows an unmet requirement, a failed relevant check, or an open high/critical finding supported by confirmed or inferred evidence.
- **Insufficient evidence:** a required check has not run, an open finding has unknown confidence, or unresolved uncertainty prevents a conclusion, and there is no supported blocker that already makes action necessary.

Follow with the highest-impact findings, exact evidence, fixes, checks performed, material unknowns, and next actions. When both a supported blocker and an unknown exist, choose `needs-action` and retain the unknown. Cite the explicit authorized acceptance decision for each accepted risk; an agent cannot accept a risk on the user's behalf. In JSON use `acceptance_source_ids` for those decision references. Avoid a numerical safety score or certification language.

For a durable record, use [review-template.md](assets/review-template.md), optionally paired with the JSON format. Make artifact creation proportional to the task. Do not copy private source contents into a public issue or repository.

For handoffs, include the goal, revision, relevant file anchors, active requirements, decisions and their origins, unresolved findings, actual checks, accepted risks, and the next executable step. Say which evidence the next agent must refresh. Do not imply automatic monitoring, shared model memory, or guaranteed detection.
