# Changelog

All notable changes to `ccs` are documented here.

## Unreleased

### Added

- Add the built-in `official` pseudo provider: `ccs use official` removes the managed provider env from `settings.json` so Claude Code falls back to the claude.ai subscription login. `ls`/`current`/`show`/`doctor` render it, shell completions offer it for `use`/`show`, and the name is reserved against `set`/`preset`/`rm`.
- Add per-project provider pinning: `ccs use <name> --project` writes the managed env into `./.claude/settings.local.json` and `ccs use --global` removes the pin while preserving everything else in the file. Secrets are only written when the file is git-ignored; managed keys defined globally but not by the pinned provider are blanked to `""` so they cannot bleed through Claude Code's per-key settings merge (this also covers `ccs use official --project`). `ccs current` becomes project-aware with a two-line view that resolves the pin back to a provider name, and `ccs doctor` reports bleed-through keys, missing gitignore coverage, and unpinned project files.

### Fixed

- Replace literal NUL/DEL bytes accidentally embedded in an awk comment so `grep`/`file` treat `bin/ccs` as text again.

## v0.7.0 - 2026-05-29

### Added

- Add `README.zh.md` and make the main README English-first with language switching.
- Add release checksum assets for the standalone `bin/ccs` installer path.
- Add regression coverage for verify HTTP status handling, plaintext HTTP warnings, checksum mismatch installs, JSON control characters, and non-string settings env values.

### Changed

- Prefer `jq` for settings rewrites when available so nested top-level settings remain readable; keep the POSIX awk writer as a fallback.
- Document the settings rewrite contract, plaintext secret boundary, and fallback installer checksum behavior.
- Keep provider env write order sourced from the single `PROVIDER_ENV_KEYS` list.
- Compare `ccs` with GUI switchers such as `cc-switch`.

### Fixed

- Escape JSON control characters in provider env values before writing `settings.json`.
- Preserve non-string, object, and array values from non-managed settings env entries during provider switches.
- Move verify auth headers out of the curl argv into a private curl config file.
- Cover verify success, auth failure, access denial, provider rejection, reachable 4xx, 5xx, and unexpected status branches.
- Warn before sending provider secrets to non-loopback plaintext HTTP endpoints.
- Create sensitive files under `umask 077` and warn if strict chmod cannot be applied.
- Pin the fallback installer to a release tag and verify the downloaded `bin/ccs` checksum before installation.
- Explicitly ignore local cache and automation directories in the repository ignore list.

## v0.6.1 - 2026-05-29

### Added

- Add a comparison guide for hand-edited settings, shell exports, proxies, gateways, and `ccs`.
- Add GitHub issue forms for bugs, feature requests, and provider recipes.
- Add a pull request template with verification and secret-handling checklist items.
- Add outreach copy for GitHub topics, awesome-list submissions, and Chinese community posts.
- Add support for provider-scoped `CLAUDE_CODE_SUBAGENT_MODEL` and `CLAUDE_CODE_EFFORT_LEVEL`.
- Add release preflight checks so tagged releases run syntax, ShellCheck, pytest, and tracked-doc safety validation before packaging.

### Changed

- Rework the README first screen around fast positioning, use cases, comparison, and SEO keywords.
- Add clearer contribution entry points for first-time contributors.
- Package the full `docs/` directory in future release archives so README links remain valid.
- Extend DeepSeek and OpenRouter presets with Claude Code subagent/effort env from their provider recipes.
- Clarify the Hugging Face recipe's single-secret `ccs` behavior against Hugging Face's two-env manual launch example.
- Update GitHub Actions workflow dependencies to Node 24-compatible major versions.

### Fixed

- Fail `ccs use` when `settings.json` cannot be written, and only update the active provider after settings are successfully applied.
- Fail `ccs rm` without deleting the provider or clearing active state when `settings.json` cannot be rewritten.
- Preserve existing non-ccs `env` JSON string escapes when rewriting `settings.json`.

## v0.6.0 - 2026-05-29

### Added

- Add `ccs preset deepseek --key KEY` for DeepSeek's Anthropic-compatible Claude Code endpoint.
- Add `ccs preset openrouter --key KEY` for OpenRouter's Claude Code endpoint.
- Add `CONTRIBUTING.md` and `SECURITY.md`.
- Add README `ccs doctor` output example for copyable troubleshooting.

### Changed

- Promote `ccs preset` in the README quickstart and provider recipes.

## v0.5.0 - 2026-05-29

### Added

- Add `ccs doctor` for local settings, dependency, active provider, and shell secret diagnostics.
- Add one-line installer script.
- Add GitHub Release workflow and release assets.
- Add provider recipes for Anthropic, DeepSeek, OpenRouter, Kimi, Hugging Face, and LiteLLM/enterprise gateways.
- Add Homebrew tap install path: `brew install Ike-li/tap/ccs`.
- Add README terminal demo GIF.

### Changed

- Reframe README positioning around the lightweight no-proxy/no-daemon workflow.
- Promote Homebrew as the primary install path.

## v0.4.0 - 2026-05-29

### Added

- Default DeepSeek's official Anthropic-compatible endpoint to `ANTHROPIC_AUTH_TOKEN`.
- Warn when an older DeepSeek provider still uses API-key mode.

### Changed

- Improve shell secret conflict guidance around `ANTHROPIC_API_KEY` and `ANTHROPIC_AUTH_TOKEN`.
