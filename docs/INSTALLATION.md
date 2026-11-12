# Installation and compatibility

The distribution source is `skills/intentweft/`. Install that entire folder, preserving its `references/`, `assets/`, `scripts/`, and `agents/` subdirectories. Copying only `SKILL.md` breaks its supporting links.

## Local installer

Run `python scripts/install.py --help` from the cloned repository. Python 3.10+ is required for bundled scripts; the skill's text can be used without Python when its optional helpers are unnecessary.

Choose `--agent codex`, `--agent claude`, or `--agent both`. Choose `--scope project --project <path>` or `--scope user`. Use `--dry-run` to inspect destinations. Paths containing spaces must be quoted. The installer does not contact a remote service, alter existing skills, configure API credentials, or modify agent settings.

Both-agent installation preflights all destinations before copying. An existing target causes a refusal. If copying fails during an installation, the installer attempts to remove only the new folders it created.

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

The core instructions use only `name` and `description` frontmatter and relative resource links. Other Agent Skills compatible hosts may be able to use the same source. Such hosts are not evaluated by this repository. Claude.ai, ChatGPT account-level skills, and remote sessions may require upload or plugin packaging rather than local folders; follow their own current instructions.

## References

- [OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code skill documentation](https://code.claude.com/docs/en/skills)
- [Agent Skills specification](https://agentskills.io/specification)
