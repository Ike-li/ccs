# Provider recipes

These recipes are starting points for Anthropic-compatible Claude Code endpoints. Run `ccs verify <name>` after adding a provider if you want to test the key, base URL, and model before switching.

`ccs` only writes Claude Code settings. It does not translate OpenAI/Gemini/Ollama protocols into Anthropic Messages API. Use a gateway such as LiteLLM or another router when the upstream endpoint is not Anthropic-compatible.

References:

- [Claude Code settings](https://docs.anthropic.com/en/docs/claude-code/settings)
- [DeepSeek Claude Code integration](https://api-docs.deepseek.com/guides/coding_agents)
- [OpenRouter Claude Code integration](https://openrouter.ai/docs/cookbook/coding-agents/claude-code-integration)
- [Kimi Code in third-party coding agents](https://www.kimi.com/code/docs/en/third-party-tools/other-coding-agents.html)
- [Hugging Face Claude Code integration](https://huggingface.co/docs/inference-providers/integrations/claude-code)

## Anthropic API

Use API-key auth for the first-party Anthropic API.

```bash
ccs set anthropic \
  --base-url https://api.anthropic.com \
  --key sk-ant-... \
  --use-api-key
ccs use anthropic
```

## DeepSeek Anthropic API

DeepSeek's Claude Code guide uses Bearer auth via `ANTHROPIC_AUTH_TOKEN`.

Fast path:

```bash
ccs preset deepseek --key sk-...
ccs use deepseek
```

Equivalent explicit setup:

```bash
ccs set deepseek \
  --base-url https://api.deepseek.com/anthropic \
  --key sk-... \
  --use-auth-token \
  --model 'deepseek-v4-pro[1m]' \
  --opus-model 'deepseek-v4-pro[1m]' \
  --sonnet-model 'deepseek-v4-pro[1m]' \
  --haiku-model deepseek-v4-flash \
  -e CLAUDE_CODE_SUBAGENT_MODEL=deepseek-v4-flash \
  -e CLAUDE_CODE_EFFORT_LEVEL=max
ccs use deepseek
```

`ccs set` defaults this official DeepSeek endpoint to auth-token mode. If an old provider was created with API-key mode, migrate it with:

```bash
ccs set deepseek --use-auth-token
ccs use deepseek
```

## OpenRouter

OpenRouter's Claude Code guide uses `https://openrouter.ai/api` and `ANTHROPIC_AUTH_TOKEN`.

Fast path:

```bash
ccs preset openrouter --key sk-or-v1-...
ccs use openrouter
```

Equivalent explicit setup:

```bash
ccs set openrouter \
  --base-url https://openrouter.ai/api \
  --key sk-or-v1-... \
  --use-auth-token \
  --opus-model '~anthropic/claude-opus-latest' \
  --sonnet-model '~anthropic/claude-sonnet-latest' \
  --haiku-model '~anthropic/claude-haiku-latest' \
  -e CLAUDE_CODE_SUBAGENT_MODEL='~anthropic/claude-opus-latest'
ccs use openrouter
```

If Claude Code has a cached Anthropic login, OpenRouter recommends running `/logout` once inside Claude Code and restarting the session.
OpenRouter also recommends blanking `ANTHROPIC_API_KEY` when using `ANTHROPIC_AUTH_TOKEN`; `ccs use openrouter --shell` prints cleanup commands for shell-level conflicts, while the settings writer removes stale managed secret values from `settings.json`.

## Kimi Code

Kimi Code's Claude Code guide uses `ANTHROPIC_BASE_URL=https://api.kimi.com/coding/` and `ANTHROPIC_API_KEY`.

```bash
ccs set kimi \
  --base-url https://api.kimi.com/coding/ \
  --key sk-... \
  --use-api-key
ccs use kimi
```

Older Moonshot Anthropic-compatible endpoints may use a different base URL. Prefer the provider's current Claude Code guide when choosing the endpoint and auth type.

## Hugging Face Inference Providers

Hugging Face's Claude Code integration uses `https://router.huggingface.co`. Its manual environment-variable example currently exports both `ANTHROPIC_AUTH_TOKEN` and `ANTHROPIC_API_KEY` to the same HF token; `ccs` keeps one active secret env to avoid Claude Code key/token conflicts, so this recipe uses auth-token mode and should be verified with your account.

```bash
ccs set hf \
  --base-url https://router.huggingface.co \
  --key hf_... \
  --use-auth-token \
  --opus-model zai-org/GLM-5.1 \
  --sonnet-model zai-org/GLM-5.1 \
  --haiku-model zai-org/GLM-5.1 \
  -e CLAUDE_CODE_SUBAGENT_MODEL=zai-org/GLM-5.1
ccs use hf
```

If Hugging Face changes its Claude Code auth requirements, prefer the upstream `hf-claude` extension or the current Hugging Face guide for that provider-specific launch path.

## LiteLLM or enterprise gateway

If your team runs a LiteLLM or internal LLM gateway with an Anthropic-format endpoint, point `ccs` at that endpoint and use the auth mode required by the gateway.

```bash
ccs set gateway \
  --base-url https://litellm.example.com \
  --key gateway-token \
  --use-auth-token \
  --model claude-sonnet-4-6
ccs use gateway
```

For local development:

```bash
ccs set local-gateway \
  --base-url http://127.0.0.1:4000 \
  --key local-token \
  --use-auth-token
ccs use local-gateway --no-verify
```

## After switching

```bash
ccs current
ccs doctor
ccs verify
```

Then restart Claude Code so it reads the updated settings.
