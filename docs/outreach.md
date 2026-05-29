# Outreach kit

This file keeps growth copy in one place so README, GitHub topics, awesome-list submissions, and community posts stay consistent.

## Positioning

One line:

> `ccs` is a tiny Claude Code provider switcher: Homebrew install, POSIX shell runtime, no proxy, no daemon, with presets for DeepSeek and OpenRouter plus `ccs doctor` for auth conflicts.

Short description:

> `ccs` switches Claude Code between Anthropic-compatible providers by writing the official `~/.claude/settings.json` env block. It is useful when you use DeepSeek, OpenRouter, Kimi, Hugging Face, LiteLLM, or an internal gateway and want repeatable provider switching without a local proxy.

## GitHub topics

Recommended topics:

```text
anthropic
anthropic-api
anthropic-compatible
api-key-management
claude
claude-code
claude-code-tools
cli
deepseek
developer-tools
homebrew
kimi
litellm
llm
llm-tools
openrouter
posix-shell
provider-switcher
provider-switching
shell-script
```

## Awesome-list pitch

PR title:

```text
Add ccs, a tiny Claude Code provider switcher
```

PR body:

```markdown
Adds `ccs`, a small POSIX shell CLI for switching Claude Code between Anthropic-compatible providers.

Why it fits:
- Works with Claude Code's official `~/.claude/settings.json` env path.
- No proxy, daemon, Node, Python, or jq runtime dependency.
- Includes Homebrew install, DeepSeek/OpenRouter presets, provider recipes, and `ccs doctor` diagnostics.
- Clearly documents boundaries: it is a switcher, not a protocol translator or secret vault.
```

Submission checklist:

- Link to the repository: `https://github.com/Ike-li/ccs`
- Prefer categories such as Claude Code tools, LLM developer tools, CLI tools, or provider utilities.
- Mention the no-proxy boundary so maintainers do not mistake it for a router.
- Avoid claiming support for non-Anthropic-compatible APIs without a gateway.

## Submission log

Submitted on 2026-05-29:

- [jqueryscript/awesome-claude-code#337](https://github.com/jqueryscript/awesome-claude-code/pull/337) - adds `ccs` under Tools & Utilities.
- [rohitg00/awesome-claude-code-toolkit#468](https://github.com/rohitg00/awesome-claude-code-toolkit/pull/468) - adds `ccs` under Ecosystem.
- [Ike-li/ccs discussion #1](https://github.com/Ike-li/ccs/discussions/1) - Chinese announcement post.

## 中文社区帖子草稿

标题：

```text
做了一个 Claude Code provider 切换小工具：ccs
```

正文：

```markdown
最近把自己切换 Claude Code provider 的脚本整理成了一个开源小工具：ccs。

它解决的问题很窄：当 provider 已经支持 Anthropic-compatible / Claude Code endpoint 时，用一个命令切换 `~/.claude/settings.json` 里的 `ANTHROPIC_BASE_URL`、`ANTHROPIC_API_KEY` 或 `ANTHROPIC_AUTH_TOKEN`。

特点：
- Homebrew 安装：`brew install Ike-li/tap/ccs`
- 内置 DeepSeek / OpenRouter preset
- `ccs doctor` 检查 settings、active provider、shell 里残留的 key/token 冲突
- 纯 POSIX shell，不需要 Node/Python/jq，不启动本地代理
- 明确边界：不做 OpenAI/Gemini/Ollama 到 Anthropic API 的协议转换

适合的人：
- 经常在 DeepSeek、OpenRouter、Kimi、Hugging Face、LiteLLM/企业网关之间切 Claude Code
- 不想手改 `~/.claude/settings.json`
- 遇到过 API key 和 auth token 冲突

仓库：https://github.com/Ike-li/ccs
```

## Maintainer reminders

- Keep README first screen focused on the switching problem, not on every command.
- Keep provider docs factual and source-aligned; provider defaults age quickly.
- Do not bury the plaintext secret boundary.
- When adding a new preset, update README, `docs/providers.md`, tests, and this outreach file if the provider becomes a headline use case.
