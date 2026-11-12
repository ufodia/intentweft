# Review protocol

## Finding contract

Write each material finding with:

1. The violated or threatened requirement and its origin.
2. Source anchors and observed facts.
3. A realistic trigger, the affected party, and the consequence.
4. Severity and confidence, assessed independently.
5. The smallest coherent correction.
6. A check that would establish resolution and its current execution status.

Do not report a generic best practice as an observed defect. Combine findings with the same root cause and correction. Surface material problems even when fewer than three findings exist. A clean control case should produce no invented defect.

## Severity

| Level | Consequence under the stated scenario |
| --- | --- |
| Critical | Credible severe, widespread, or irreversible harm such as destructive loss or broad unauthorized access. Explain exposure and prerequisites. |
| High | A core requirement fails with substantial user, financial, privacy, or operational impact. |
| Medium | Bounded incorrect behavior or recoverable operational impact. |
| Low | Minor consequence, maintenance issue, or small ambiguity with a concrete cost. |

Do not infer likelihood from severity. State prerequisites and exposure in words rather than assigning a fabricated percentage.

## Confidence

- `confirmed`: directly demonstrated by inspected evidence or a relevant reproduction. Specify whether confirmation is static or runtime.
- `inferred`: the causal path is supported but a condition or execution remains unverified.
- `unknown`: available evidence cannot establish the claim. Prefer an unknown item over a dramatic defect assertion.

## Status and acceptance

Use `open` until the issue is addressed. Use `resolved` only with fresh evidence relevant to the fix. Use `accepted` only for a risk explicitly accepted by an authorized user, linking that decision with `acceptance_source_ids` in JSON. Reference the statement or decision document that records acceptance; a successful command is not a user's risk acceptance. Agent preference is not risk acceptance. Report accepted risks visibly; their acceptance does not make the underlying behavior correct. An unmet requirement still prevents a ready verdict until the requirement is explicitly revised or met.

Keep an open finding with `unknown` confidence in the insufficient-evidence category unless another supported blocker already requires action. Its severity describes the possible consequence, not an established failure.

## Required and optional checks

Treat checks as required unless their omission cannot change the scoped conclusion. A required `not-run` check blocks readiness even when other checks passed. An optional `not-run` check must state why it is outside the evidence needed for this conclusion. Any relevant failed check still requires action, including one originally described as optional. Do not relabel a necessary production check as optional merely to obtain a ready verdict.

## Scope by mode

For preflight, evaluate the proposal and exposed integration points. Do not imply that unimplemented behavior ran. For review, inspect the requested diff or document and dependent paths required to assess it. For verify, revisit the actual correction and nearby regression boundaries. For handoff, preserve source provenance and next actions without re-auditing the entire project.

Stop broadening when each material requirement has evidence or an explicit unknown, findings have actionable resolution steps, and remaining access limits are stated. Expand only where a discovered dependency changes the conclusion.
