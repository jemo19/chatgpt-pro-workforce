# Contributing

Thanks for helping improve ChatGPT Pro Workforce for Codex.

## Before changing the skill

- Read [SECURITY.md](SECURITY.md) and the runtime
  [security boundary](chatgpt-pro-workforce/references/security-and-authority.md).
- Use synthetic fixtures. Never commit credentials, private prompts, browser
  profiles, live conversation URLs, local capability reports, or customer data.
- Keep `chatgpt-pro-workforce/SKILL.md` concise and route conditional detail to
  an existing or clearly justified reference.
- Preserve the exact skill name and invocation unless a migration is explicitly
  planned and documented.
- Do not make a platform adapter mandatory merely because it exists on one
  workstation.
- Tool availability never implies permission.

## Development workflow

Python 3.10 or newer and GNU Make are sufficient; the runtime and tests do not
download dependencies.

```bash
make check
```

When the current Codex `skill-creator` validator is installed, also run:

```bash
make validate-authoritative
```

Build and then verify the deterministic release set with:

```bash
make verify-package
```

That verifies the ZIP, SHA-256 sidecar, and inventory as one release. Do not
publish a ZIP without its matching sidecars.

## Pull requests

- Keep one coherent behavior change per pull request.
- Say what changed for the user and which safety boundaries stayed in place.
- Add or update a meaningful behavior test when decisions or state transitions
  change; avoid tests that only match decorative wording.
- Document live versus simulated evidence truthfully.
- Identify platform testing that was not performed.
- Update `CHANGELOG.md` for user-visible changes.

All checks must pass, Markdown links must resolve, and the installable skill
must contain no authoring-only files before review.
