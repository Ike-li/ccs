# Changelog

All notable changes to `ccs` are documented here.

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
