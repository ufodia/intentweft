# Contributing

Keep the portable skill concise and the public examples synthetic. Submit a focused pull request explaining the concrete failure the change addresses, the resulting behavior, and the validation performed.

Put reusable agent instructions in `skills/intentweft/`. Keep installation and contributor documentation at the repository level. Use English throughout. Preserve common `SKILL.md` frontmatter and avoid required vendor-specific tools, hidden remote services, and claims of guaranteed detection.

Run:

```bash
python scripts/check_repository.py
python -m unittest discover -s tests -v
```

When changing review behavior, also run relevant fixtures in fresh agent sessions and include the raw responses or a privacy-safe summary. Keep expected answers outside the fixture provided to the agent. State the host and model actually used. Add a clean control when adding a defect case so improvements do not reward invented findings.

Do not commit customer data, secrets, private project reports, or unverified performance claims. See `evals/README.md` for the behavioral evaluation procedure.
