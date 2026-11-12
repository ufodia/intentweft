# Durable report format

Use Markdown for the human decision. Add JSON when machine-checkable references and file freshness are useful. Both formats describe the same scoped assessment. Start with [the example](../assets/report.example.json), replacing its synthetic contents and dates with real observations.

## JSON fields

| Field | Contents |
| --- | --- |
| `schema_version` | Integer `1` |
| `review` | `mode`, a nonempty `scope`, and `verdict` |
| `sources` | Source IDs, kinds, locators, and freshness information |
| `requirements` | Active requirement IDs, text, source IDs, and status |
| `findings` | ID, nonempty `title`, `requirement_ids`, `source_ids`, severity, confidence, status, scenario, impact, action, verification; `acceptance_source_ids` when accepted |
| `unknowns` | ID, question, boolean `blocking`, and `next_step` |
| `checks` | ID, description, status, source IDs, detail, and optional boolean `required` (defaults to `true`) |
| `next_actions` | Nonempty action strings, or an empty list when none remain |

All lists must be present; findings, unknowns, checks, and next_actions may be empty. At least one source and one requirement are required. Keep IDs unique across the report. All referenced IDs must exist. Use nonempty source references for requirements and findings; a check may have none only if `not-run`.

Provide standard JSON with no duplicate object keys. The file reader rejects duplicate keys at every nesting level and nonstandard `NaN` or `Infinity` constants rather than silently selecting a conflicting value.

Use IDs consisting of the category prefix followed by a positive integer without leading zeroes: `S1` for sources, `R1` for requirements, `F1` for findings, `U1` for unknowns, and `C1` for checks. IDs such as `source-1`, `R0`, and `C01` are rejected by the helper.

Use source kinds `file`, `statement`, `external`, and `execution`. For `file`, provide a root-relative POSIX path and a SHA-256 hash from the helper; put line/section anchors in requirement text or finding narrative. Use `/` separators on every operating system, including Windows. Backslashes, absolute paths, empty or `.` / `..` components, Windows device names such as `NUL` and `COM1`, components ending in a dot or space, control characters, and the Windows-invalid characters `< > : " | ? *` are rejected. Ordinary Unicode characters and embedded spaces are supported; quote locators containing spaces in shell commands.

For other source kinds, provide a nonempty locator and `observed_at` as either `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS` followed by an optional fractional second (`.` plus one to six digits) and a required timezone (`Z` or an offset of `+HH:MM` / `-HH:MM`). Examples are `2026-11-13T09:30:00Z` and `2026-11-13T09:30:00.123456+02:00`. Compact dates, week dates, and timestamps without a timezone are rejected. For executions, the locator identifies the command or retained log; describe its actual result in the check detail. Do not embed credentials or private transcript excerpts.

Clock hours must be `00` through `23`; minutes and seconds must be `00` through `59`. The helper rejects `24:00:00` and leap-second notation consistently across supported Python versions. Offset hours and minutes use the same `00` through `23` and `00` through `59` bounds.

Use requirement status `met`, `unmet`, or `unknown`; finding status `open`, `resolved`, or `accepted`; confidence `confirmed`, `inferred`, or `unknown`; severity `critical`, `high`, `medium`, or `low`; check status `passed`, `failed`, or `not-run`.

For an `accepted` finding, provide a nonempty `acceptance_source_ids` list identifying the specific decision accepting the risk. These references must resolve to sources of kind `file`, `statement`, or `external`; an execution result cannot establish acceptance. The helper validates the references and source kinds, not the decision's authenticity, scope, or authority. Cite the relevant decision anchor in the finding narrative. Risk acceptance does not change an unmet requirement to met.

A check is required unless it explicitly sets `"required": false`. A required check with status `not-run` leaves readiness unestablished. Use an optional check only when it is unnecessary to establish the scoped requirements, and explain that limit in `detail`. An optional check that did not run cannot be used as evidence that a requirement is met. Any failed check retained in the scoped report requires action, even if optional.

## Complete finding example

This synthetic report demonstrates every required finding field. `S1` supplies the requirement, `S2` records a failed check, and `F1` links both sources to `R1`. Replace all synthetic observations before using it for a real assessment.

```json
{
  "schema_version": 1,
  "review": {
    "mode": "review",
    "scope": "Synthetic retention test only; production behavior not assessed",
    "verdict": "needs-action"
  },
  "sources": [
    {"id": "S1", "kind": "statement", "locator": "Synthetic requirement: delete activity older than 30 days", "observed_at": "2026-11-13"},
    {"id": "S2", "kind": "execution", "locator": "Synthetic retained log: retention test in a disposable fixture", "observed_at": "2026-11-13T09:30:00Z"}
  ],
  "requirements": [
    {"id": "R1", "text": "Delete activity older than 30 days", "source_ids": ["S1"], "status": "unmet"}
  ],
  "findings": [
    {
      "id": "F1",
      "title": "Retention test leaves an expired activity record",
      "requirement_ids": ["R1"],
      "source_ids": ["S1", "S2"],
      "severity": "high",
      "confidence": "confirmed",
      "status": "open",
      "scenario": "The fixture starts with a record aged 31 days and runs the deletion job; the record remains afterward.",
      "impact": "The deletion job fails the stated retention requirement in this fixture.",
      "action": "Correct the expired-record selection or deletion path.",
      "verification": "Rerun the fixture after the correction and confirm that the expired record is absent."
    }
  ],
  "unknowns": [],
  "checks": [
    {"id": "C1", "description": "Run the synthetic retention fixture", "status": "failed", "source_ids": ["S2"], "required": true, "detail": "The retained synthetic log reports that the 31-day-old record remained; coverage is limited to this fixture."}
  ],
  "next_actions": ["Fix the deletion path and rerun the retention fixture"]
}
```

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

| Exit status | Meaning |
| --- | --- |
| `0` | Snapshot written, or report valid and current. A valid report with verdict `needs-action` or `insufficient-evidence` also returns `0`. |
| `1` | Invalid input or report, stale file evidence, or an I/O failure. |
| `2` | Invalid command arguments. |

Read the report verdict separately from the exit status. Successful validation establishes the supported structure and file freshness only.

Forced replacement writes are staged in a sibling temporary file and published only after the write succeeds. Failed new writes clean up their partial output when possible. Output paths containing symlinks or reparse points, reserved Windows device names, alternate data stream syntax (a colon outside the Windows drive anchor), unsafe Windows filename components, or nonregular output files are rejected. Explicit parent navigation such as `../sources.json` is supported for output paths. The helper does not provide a general filesystem transaction or protect against concurrent hostile changes to the working directory.

CLI output retains the environment's chosen encoding. Characters that encoding cannot represent are escaped in console messages so a successful file operation does not become a Unicode printing failure; JSON files are still written as UTF-8.

Keep private reports in an appropriate private workspace. Report paths and file hashes can reveal project metadata even though the helper does not store file contents.
