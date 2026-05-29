# ccs compared with other Claude Code provider workflows

`ccs` is intentionally small: it switches Claude Code between Anthropic-compatible providers by writing the official `~/.claude/settings.json` environment block. It is not a protocol translator, router, proxy, or secret vault.

## Quick decision

Use `ccs` when:

- Your provider already exposes an Anthropic-compatible Claude Code endpoint.
- You switch between Anthropic, DeepSeek, OpenRouter, Kimi, Hugging Face, LiteLLM, or an internal gateway.
- You want a repeatable command instead of hand-editing `settings.json`.
- You need diagnostics for API key vs bearer token conflicts.
- You prefer no daemon, no local port, and no Node/Python runtime for the switcher itself.

Do not use `ccs` as the main tool when:

- You need to translate OpenAI, Gemini, Ollama, or custom chat APIs into Anthropic Messages API.
- You need centralized encrypted secret storage, rotation, audit logs, or team policy enforcement.
- You need model routing, fallback, rate limiting, or request rewriting.
- You need native Windows support without a POSIX shell environment.

## Comparison matrix

| Approach | Best for | Strengths | Tradeoffs |
|---|---|---|---|
| Hand-edit `~/.claude/settings.json` | One-off experiments | No extra tool; fully transparent | Easy to leave stale env values, hard to repeat, no validation, no recipes |
| Shell `export ANTHROPIC_*` scripts | Temporary sessions | Simple and familiar | State disappears across terminals; conflicts with settings can be confusing |
| `.env` / direnv / secret helpers | Per-project env management | Works well with existing shell workflows | Does not understand Claude Code provider semantics or model aliases |
| Local proxy / router | Protocol translation and routing | Can bridge non-Anthropic APIs, add fallback, logging, and policy | Requires a running process, local port, more moving parts, and extra security review |
| Full gateway such as LiteLLM | Team-scale model access | Centralizes models, auth, budgets, routing | Solves a different layer; users still need a clean Claude Code client setup |
| `ccs` | Client-side provider switching | Small POSIX shell CLI, Homebrew install, recipes, `doctor`, official settings path | Plaintext settings by design; no protocol translation; scoped to Claude Code env settings |

## Where `ccs` is stronger

- **Fast first run**: `brew install Ike-li/tap/ccs`, `ccs preset deepseek --key ...`, `ccs use deepseek`.
- **Low operational surface**: no background process, no listening port, no runtime dependency.
- **Claude Code-specific semantics**: knows `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, and `/model` alias env vars.
- **Conflict diagnosis**: `ccs doctor` checks settings, active provider, shell secret conflicts, and common provider mistakes.
- **Reviewable state**: provider files are plain `KEY=value`; the active provider is explicit.
- **Safe switching behavior**: when switching auth modes, `ccs` removes the other managed secret env from `settings.json`.

## Where `ccs` is weaker by design

- **Plaintext secret storage**: Claude Code settings and `ccs` provider files contain plaintext keys. `ccs` sets restrictive file permissions where possible, but it is not an encrypted vault.
- **No protocol conversion**: if an upstream only speaks OpenAI-compatible chat completions, use a gateway/router first.
- **No request path control**: `ccs` does not log, retry, route, rewrite, or rate-limit requests.
- **No central policy**: teams that need shared budgets, audit logs, or forced model allowlists should put those controls in the provider/gateway layer.
- **Provider recipes can age**: endpoints, auth modes, and model names change. `ccs preset` covers common paths, but provider docs remain the source of truth.

## Recommended combinations

| Scenario | Recommended setup |
|---|---|
| Individual user testing DeepSeek or OpenRouter | `ccs preset ...`, then `ccs use ...` |
| Team with an internal Anthropic-compatible gateway | Gateway handles policy; `ccs` handles each developer's Claude Code settings |
| Team using LiteLLM for model routing | LiteLLM handles translation/routing; `ccs` points Claude Code at LiteLLM |
| Security-sensitive organization | Use managed key distribution or a vault workflow, then feed short-lived keys into `ccs set --key -` |
| Debugging provider setup | `ccs doctor`, then `ccs verify <name>` |

## Evaluation checklist

When comparing `ccs` with another provider switcher, check:

- Does it write Claude Code's supported settings path or rely on shell state only?
- Does it clean up stale `ANTHROPIC_API_KEY` vs `ANTHROPIC_AUTH_TOKEN` conflicts?
- Does it explain plaintext secret boundaries clearly?
- Does it require a daemon, proxy, local port, Node, Python, or jq at runtime?
- Does it provide provider recipes and tests for those recipes?
- Does it separate client-side switching from gateway/proxy responsibilities?

The short version: choose `ccs` when the endpoint already speaks Claude Code's Anthropic-compatible language and you want the smallest reliable switcher around that fact.
