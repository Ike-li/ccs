# Security Policy

## Supported versions

Security fixes are made on the latest released version.

## Secret handling

`ccs` manages Claude Code provider settings and therefore handles provider keys/tokens.

Current security semantics:

- Provider files under `~/.config/ccs/providers/*.conf` contain plaintext keys.
- Claude Code `~/.claude/settings.json` contains the active provider key/token in plaintext.
- `ccs` attempts to write provider files and settings with owner-only permissions where the platform allows it.
- `ccs show` masks keys by default; use `--show-key` only when you intentionally need to inspect the full value.
- `ccs doctor`, `ccs ls`, and normal switch messages must not print full secret values.

Treat `~/.config/ccs` and `~/.claude/settings.json` as sensitive files. Do not commit them, paste them into public issues, or sync them to systems where plaintext API keys are not acceptable.

## Reporting a vulnerability

Please do not disclose vulnerabilities or real provider keys in public issues.

Preferred paths:

1. Use GitHub private vulnerability reporting for this repository if it is available.
2. If private reporting is not available, open a public issue with only a minimal description and no secrets, then ask the maintainer for a private contact path.

When reporting, include:

- `ccs --version`
- Operating system and shell
- The smallest command sequence that demonstrates the issue
- Whether any secret was exposed, written to an unexpected place, or printed to output

## Out of scope

These are usually not `ccs` vulnerabilities by themselves:

- A provider rejecting a key or model.
- Claude Code behavior after it reads settings written by `ccs`.
- Plaintext storage in `~/.claude/settings.json`, which is part of the current documented security model and called out in the README.
