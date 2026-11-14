# Installation and compatibility

The distribution source is `skills/intentweft/`. Install that folder, preserving its `references/`, `assets/`, `scripts/`, and `agents/` subdirectories. Copying only `SKILL.md` breaks its supporting links. Generated `__pycache__` directories and `*.pyc` / `*.pyo` files are unnecessary; the installer excludes them and preserves the remaining package files.

## Local installer

Run `python scripts/install.py --help` from the cloned repository. Python 3.10+ is required for bundled scripts; the skill's text can be used without Python when its optional helpers are unnecessary.

Choose `--agent codex`, `--agent claude`, or `--agent both`. Choose `--scope project --project <path>` or `--scope user`. Use `--dry-run` to inspect destinations. Paths containing spaces must be quoted. The installer does not contact a remote service, alter existing skills, configure API credentials, or modify agent settings.

Both-agent installation preflights all destinations before copying. An existing target causes a refusal. If copying fails or you interrupt it with Ctrl+C, the installer attempts to remove only the new skill folders and empty parent folders it created. Cleanup handles read-only copied files. If cleanup cannot complete, inspect the reported paths before retrying.

Cleanup can run only when the process catches the error or interruption. Forced process termination and power loss cannot run cleanup; inspect the destination if such an event occurs. Python-generated `__pycache__` directories and `.pyc` / `.pyo` files are excluded from source validation and installation. All other source files are copied.

Before copying, the installer validates this distribution's deliberately limited two-field `SKILL.md` frontmatter: the plain `name: intentweft` and a nonempty `description`. Descriptions may use plain English text or JSON-compatible double quoting. Missing, duplicate, unsupported, or malformed fields are rejected. This is a check of the bundled distribution, not a general YAML validator for arbitrary third-party skills.

## Manual installation

| Agent | Copy the complete source folder to |
| --- | --- |
| Codex, one project | `<project>/.agents/skills/intentweft` |
| Codex, user scope | `~/.agents/skills/intentweft` |
| Claude Code, one project | `<project>/.claude/skills/intentweft` |
| Claude Code, user scope | `~/.claude/skills/intentweft` |

Here `~` means your operating-system home folder. Prefer one scope per agent to avoid ambiguous duplicate installations. The repository does not contain automatically loaded copies of its own skill; install explicitly into the project you want reviewed.

## Confirm availability

In Codex select the available skill or invoke `$intentweft`. In Claude Code invoke `/intentweft`. If a session does not discover a newly added skill, check that `SKILL.md` is at the exact destination above and consult the host's current skill discovery documentation. Organization policies or restricted modes may prevent local skills from loading.

## Update and remove

Before updating, preserve local edits in your existing installed folder. Compare it with the new repository version, then replace only that skill folder after reviewing the differences. The installer deliberately provides no automatic overwrite flag.

To remove IntentWeft, delete only the installed `intentweft` folder from the relevant destination. Preserve any review reports you want to retain; reports are separate from the installed skill. Do not remove the parent `.agents/skills` or `.claude/skills` folder.

## Other hosts

The core instructions use only `name` and `description` frontmatter and relative resource links. Other Agent Skills compatible hosts may be able to use the same source. These hosts are not evaluated by this repository.

### ChatGPT

On an eligible account or workspace, ChatGPT offers **Skills → Create → Upload from your computer**. Review and upload the complete `skills/intentweft/` skill package, including its supporting directories, using the format the upload flow requests. ChatGPT scans uploaded skills before making them available; access and upload permissions depend on the account and workspace. See [Skills in ChatGPT](https://help.openai.com/en/articles/20001066-skills-in-chatgpt) for the current workflow.

Local Codex installation does not automatically install an account-level ChatGPT skill. ChatGPT's ability to access local files or run the optional Python helper depends on the selected environment and its permissions. This repository has not tested the ChatGPT upload or runtime, so verify availability and the workflow in your own environment.

Claude.ai and remote sessions may also require account-level installation or plugin packaging rather than local folders; follow their current instructions.

## References

- [OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code skill documentation](https://code.claude.com/docs/en/skills)
- [Agent Skills specification](https://agentskills.io/specification)
