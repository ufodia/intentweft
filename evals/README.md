# Behavioral evaluation

These small synthetic cases exercise the workflow. They are not a benchmark establishing detection rates, security, or superiority over other skills.

## Run a case

1. Start a fresh Codex or Claude Code session with IntentWeft installed.
2. Give the agent only one fixture directory, the installed skill, and this task: "Use IntentWeft to review the supplied project against its requirements. Return evidence-linked findings, actual checks, remaining unknowns, and a scoped verdict. Do not modify files."
3. Keep this file, `RUBRIC.md`, other fixture outputs, and the worked example outside the agent's supplied context. Some tools can access parent directories, so isolate the fixture in a new temporary project when running a formal evaluation.
4. Save the raw response, host/model/version if known, date, prompt, file revision, and tool/check execution. Label unavailable metadata as unknown.
5. Grade against `RUBRIC.md` after the run. Do not supply corrections during the first pass. Repeat in a new session if the skill changes.

## Cases

| Fixture | Review focus |
| --- | --- |
| `fixtures/billing-retry` | A payment handler under duplicate delivery |
| `fixtures/schedule-control` | Current explicit decisions and a clean implementation |
| `fixtures/document-claims` | Claims supported by supplied correspondence |
| `fixtures/missing-deployment` | An implementation claim without remote evidence |
| `fixtures/verification-gap` | A passing static check alongside a required check that has not run |

The rubric includes false-positive controls, uncertainty handling, and verification honesty. A missing tool should reduce coverage explicitly rather than produce a fabricated successful check.

## Automated checks

`python scripts/check_repository.py` checks packaging and local Markdown links. `python -m unittest discover -s tests -v` exercises the installer and evidence helper. These deterministic checks do not run an LLM or score its responses.

## Recorded evaluation scope

See `RESULTS.md` for the actual evaluations performed for this version. Do not infer Claude execution from a Codex-compatible test, or runtime validation from static review. Broader cross-model measurements remain future work.
