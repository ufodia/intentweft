# Durable report format

Use Markdown for the human decision. Add JSON when machine-checkable references and file freshness are useful. Both formats describe the same scoped assessment. Start with [the example](../assets/report.example.json), replacing its synthetic contents and dates with real observations.

## JSON fields

| Field | Contents |
| --- | --- |
| `schema_version` | Integer `1` |
| `review` | `mode`, a nonempty `scope`, and `verdict` |
| `sources` | Source IDs, kinds, locators, and freshness information |
| `requirements` | Active requirement IDs, text, source IDs, and status |
| `findings` | Finding IDs, requirement/source IDs, severity, confidence, status, scenario, impact, action, verification |
| `unknowns` | ID, question, boolean `blocking`, and `next_step` |
| `checks` | ID, description, status, source IDs, and detail |
| `next_actions` | Nonempty action strings, or an empty list when none remain |

All lists must be present; findings, unknowns, checks, and next_actions may be empty. At least one source and one requirement are required. Keep IDs unique across the report. All referenced IDs must exist. Use nonempty source references for requirements and findings; a check may have none only if `not-run`.

Use source kinds `file`, `statement`, `external`, and `execution`. For `file`, provide a root-relative POSIX path and a SHA-256 hash from the helper; put line/section anchors in requirement text or finding narrative. For other kinds provide a nonempty locator and `observed_at` as an ISO date or timestamp. For executions, the locator identifies the command or retained log; describe its actual result in the check detail. Do not embed credentials or private transcript excerpts.

Use requirement status `met`, `unmet`, or `unknown`; finding status `open`, `resolved`, or `accepted`; confidence `confirmed`, `inferred`, or `unknown`; severity `critical`, `high`, `medium`, or `low`; check status `passed`, `failed`, or `not-run`.

## Verdict consistency

Select `needs-action` if any requirement is unmet, any check failed, or any high/critical finding is open. Otherwise select `insufficient-evidence` if any requirement is unknown, any unknown blocks, or no check has actually run. Otherwise select `ready`. Medium/low findings and accepted risks must still be disclosed. Requirements listed in JSON are active; preserve superseded requirements in the narrative history rather than listing them as unmet active requirements.

This is a consistency rule, not an automated risk judgment. The agent must establish scope, choose relevant checks, and assess evidence. A structural pass cannot validate those choices.

## Commands

```text
python <skill-dir>/scripts/evidence.py snapshot --root <project> --out <sources.json> policy.md src/handler.py
python <skill-dir>/scripts/evidence.py check <report.json> --root <project>
```

`snapshot` emits a `sources` object for explicitly named files. Merge those entries into the report, keeping IDs unique. Existing outputs are protected; use `--force` only when replacing your intended generated snapshot. `check` validates the supported structure, references, verdict consistency, and file hashes under the supplied root. It does not run project tests or check the truth, completeness, or authority of statements.

Keep private reports in an appropriate private workspace. Report paths and file hashes can reveal project metadata even though the helper does not store file contents.
