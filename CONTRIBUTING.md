# Contributing

Thanks for helping improve `ccs`.

`ccs` is intentionally small: it is a POSIX shell provider switcher for Claude Code settings, not a local proxy or protocol translation gateway. Contributions should keep that boundary clear.

## Development setup

No runtime dependencies are required for `bin/ccs`. Tests use Python and pytest.

```bash
sh -n bin/ccs install.sh
shellcheck -s sh bin/ccs install.sh
uv run --no-project --with pytest pytest tests/test_cli.py
uv run --no-project --with ruff ruff check tests
uv run --no-project --with ruff ruff format --check tests
```

If you do not use `uv`, install `pytest` and `ruff` in your preferred Python environment and run the same commands.

## Good first contributions

Useful small contributions include:

- Add or correct a provider recipe in `docs/providers.md`.
- Improve `ccs doctor` diagnostics for a real failure mode.
- Add a regression test for a CLI edge case.
- Improve shell completion coverage.
- Tighten README or troubleshooting copy after trying the first-run path.

Please use the GitHub issue templates when reporting bugs, requesting features, or suggesting provider recipes. They are designed to collect the version, install path, auth mode, and safe redacted diagnostics without exposing provider keys.

## Pull request guidelines

- Keep changes focused and reviewable.
- Add or update tests for CLI behavior changes.
- Update README/docs when user-visible commands, files, or safety semantics change.
- Prefer POSIX `sh` features over Bash-specific syntax.
- Avoid new dependencies unless there is a strong reason and a clear maintenance plan.

## Provider recipes

Provider defaults change over time. When adding or changing a recipe:

- Link to the provider's current Claude Code or Anthropic-compatible documentation.
- Include the expected auth mode: `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`.
- Include model defaults only when the provider documents or strongly recommends them.
- Add tests when the recipe is exposed through `ccs preset`.

## Commit messages

Maintainer commits use the repository's decision-record style with trailers such as `Constraint:`, `Rejected:`, `Tested:`, and `Not-tested:`. External contributions do not need to copy that format exactly, but please include what changed and how you verified it.
