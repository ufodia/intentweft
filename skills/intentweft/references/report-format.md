# Durable report format

Use Markdown for the human decision. Add JSON when machine-checkable references and file freshness are useful. Both formats describe the same scoped assessment. Start with [the example](../assets/report.example.json), replacing its synthetic contents and dates with real observations.

## JSON fields

| Field | Contents |
| --- | --- |
| `schema_version` | Integer `1` |
| `review` | `mode`, a nonempty `scope`, and `verdict` |
| `sources` | Source IDs, kinds, locators, and freshness information |
| `requirements` | Active requirement IDs, text, source IDs, and status |
| `findings` | Finding IDs, requirement/source IDs, severity, confidence, status, scenario, impact, action, verification; acceptance source IDs when accepted |
| `unknowns` | ID, question, boolean `blocking`, and `next_step` |
| `checks` | ID, description, status, source IDs, detail, and optional boolean `required` (defaults to `true`) |
| `next_actions` | Nonempty action strings, or an empty list when none remain |

All lists must be present; findings, unknowns, checks, and next_actions may be empty. At least one source and one requirement are required. Keep IDs unique across the report. All referenced IDs must exist. Use nonempty source references for requirements and findings; a check may have none only if `not-run`.

Provide standard JSON with no duplicate object keys. The file reader rejects duplicate keys at every nesting level and nonstandard `NaN` or `Infinity` constants rather than silently selecting a conflicting value.

Use IDs consisting of the category prefix followed by a positive integer without leading zeroes: `S1` for sources, `R1` for requirements, `F1` for findings, `U1` for unknowns, and `C1` for checks. IDs such as `source-1`, `R0`, and `C01` are rejected by the helper.

Use source kinds `file`, `statement`, `external`, and `execution`. For `file`, provide a root-relative POSIX path and a SHA-256 hash from the helper; put line/section anchors in requirement text or finding narrative. For other kinds provide a nonempty locator and `observed_at` as an ISO date or timestamp. For executions, the locator identifies the command or retained log; describe its actual result in the check detail. Do not embed credentials or private transcript excerpts.

Use requirement status `met`, `unmet`, or `unknown`; finding status `open`, `resolved`, or `accepted`; confidence `confirmed`, `inferred`, or `unknown`; severity `critical`, `high`, `medium`, or `low`; check status `passed`, `failed`, or `not-run`.

For an `accepted` finding, provide a nonempty `acceptance_source_ids` list identifying the specific decision accepting the risk. These references must resolve to sources of kind `file`, `statement`, or `external`; an execution result cannot establish acceptance. The helper validates the references and source kinds, not the decision's authenticity, scope, or authority. Cite the relevant decision anchor in the finding narrative. Risk acceptance does not change an unmet requirement to met.

A check is required unless it explicitly sets `"required": false`. A required check with status `not-run` leaves readiness unestablished. Use an optional check only when it is unnecessary to establish the scoped requirements, and explain that limit in `detail`. An optional check that did not run cannot be used as evidence that a requirement is met. Any failed check retained in the scoped report requires action, even if optional.

## Verdict consistency

Select `needs-action` if any requirement is unmet, any check failed, or an open high/critical finding has confidence `confirmed` or `inferred`.

Otherwise select `insufficient-evidence` if any requirement is unknown, any unknown blocks, any required check did not run, any open finding has confidence `unknown`, or no check has actually run. An unknown-confidence finding does not become a demonstrated failure because its potential severity is high.

Otherwise select `ready`. Medium/low findings and accepted risks must still be disclosed. Requirements listed in JSON are active; preserve superseded requirements in the narrative history rather than listing them as unmet active requirements.

The initial pre-release schema retains version `1` while these validation rules are tightened. Reports using `accepted` findings need the acceptance references described above; reports with omitted `required` fields treat those checks as required.

This is a consistency rule, not an automated risk judgment. The agent must establish scope, choose relevant checks, and assess evidence. A structural pass cannot validate those choices.

## Commands

```text
python <skill-dir>/scripts/evidence.py snapshot --root <project> --out <sources.json> policy.md src/handler.py
python <skill-dir>/scripts/evidence.py check <report.json> --root <project>
```

`snapshot` emits a `sources` object for explicitly named files. Merge those entries into the report, keeping IDs unique. Existing outputs are protected; use `--force` only when replacing your intended generated snapshot. `check` validates the supported structure, references, verdict consistency, and file hashes under the supplied root. It does not run project tests or check the truth, completeness, or authority of statements.

Forced replacement writes are staged in a sibling temporary file and published only after the write succeeds. Failed new writes clean up their partial output when possible. Output paths containing symlinks or reparse points, reserved Windows device names, and nonregular output files are rejected. The helper does not provide a general filesystem transaction or protect against concurrent hostile changes to the working directory.

Keep private reports in an appropriate private workspace. Report paths and file hashes can reveal project metadata even though the helper does not store file contents.
