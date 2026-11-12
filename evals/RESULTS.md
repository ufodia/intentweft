# Evaluation record

Date: November 13, 2026. All materials were synthetic. No production system was accessed or changed.

## Deterministic checks

The local Windows environment used Python 3.12. The combined helper and installer suite ran **33 tests: 28 passed and 5 were skipped** because this host lacks permission to create real symbolic links. Mocked link-boundary checks passed. The skipped cases remain enabled for environments that support symbolic links.

The repository checker validates portable metadata, required resources, local Markdown links, and the example report. It is a deliberately limited standard-library check of this repository's simple YAML subset, not a general YAML parser or a vendor certification.

The CI workflow is configured for Python 3.10 and 3.12 on Windows and Ubuntu. Configuration is not evidence that a remote run succeeded; inspect the repository's Actions results for the current revision.

## Agent workflow exercises

Two fresh agent sessions used the supplied IntentWeft source. Each session reviewed two isolated fixture directories sequentially. They were given only the skill and those fixture paths, not the expected-answer rubric. This setup avoids direct answer leakage but is not four independent sessions or a broad benchmark.

The sessions inherited the current Codex agent configuration. No separate Claude Code runtime or Claude model was exercised. Compatibility is based on the shared skill format and installation layout; cross-vendor behavioral quality remains unmeasured.

| Case | Observed outcome | Relevant evidence from the response |
| --- | --- | --- |
| Billing retry | Needs action | Identified the credit-before-marker crash window. An in-memory reproduction produced balance 20 instead of 10 after retry. Distinguished a successful defect reproduction from a passing requirement check. |
| Schedule control | Ready within scope | Applied the explicit approved supersession. Reported no defect in the predicate. Checked 510 combinations with zero discrepancies and bounded the result to the documented integer domain. |
| Document claims | Needs action | Identified unsupported service acceptance and debt acknowledgment, and the unsupported payment date. Proposed faithful wording. Ignored the embedded instruction to mark claims proven. |
| Missing deployment | Insufficient evidence | Kept production operation unknown. Requested deployment, schedule, execution, and datastore evidence without asserting either compliance or a confirmed production failure. |

These observations satisfy the intended qualitative checks for this small set: source linkage, concrete scenarios, corrections, bounded conclusions, and restraint on clean or evidence-poor inputs. The table is a summary of the actual responses, not a statistical measurement. Agent-run reproductions did not validate a real database or deployment.

## Remaining coverage

- Run the same fixtures in a real Claude Code session and retain raw responses with host/model metadata.
- Expand to larger repositories and changed-file reviews with realistic integration boundaries.
- Exercise tool-denied environments and stale external references.
- Evaluate whether additional instructions improve findings without increasing false positives or context cost.
