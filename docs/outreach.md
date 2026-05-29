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
- [LangGPT/awesome-claude-code#79](https://github.com/LangGPT/awesome-claude-code/pull/79) - adds `ccs` to English and Chinese Development Tools & Utilities.
- [Ike-li/ccs discussion #1](https://github.com/Ike-li/ccs/discussions/1) - Chinese announcement post.

Drafted on 2026-05-29:

- V2EX, Juejin, and Sspai reuse drafts are prepared below. They still need platform account selection and explicit public-post approval before publishing.

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

## 中文平台复用稿

### V2EX

节点建议：

- `programmer`
- `create`
- `ai`

标题：

```text
做了一个 Claude Code provider 切换小工具：ccs
```

正文：

~~~markdown
最近把自己切换 Claude Code provider 的脚本整理成了一个开源小工具：ccs。

它解决的问题很窄：当 provider 已经支持 Anthropic-compatible / Claude Code endpoint 时，用一个命令切换 `~/.claude/settings.json` 里的 `ANTHROPIC_BASE_URL`、`ANTHROPIC_API_KEY` 或 `ANTHROPIC_AUTH_TOKEN`。

适合：
- 经常在 DeepSeek、OpenRouter、Kimi、Hugging Face、LiteLLM/企业网关之间切 Claude Code
- 不想手改 `~/.claude/settings.json`
- 遇到过 API key 和 auth token 冲突

特点：
- Homebrew 安装：`brew install Ike-li/tap/ccs`
- 内置 DeepSeek / OpenRouter preset
- `ccs doctor` 检查 settings、active provider、shell 残留 key/token 冲突
- POSIX shell，不需要 Node/Python/jq，不启动本地代理
- 明确边界：不做 OpenAI/Gemini/Ollama 到 Anthropic API 的协议转换

快速开始：

```bash
brew install Ike-li/tap/ccs
ccs init
ccs preset deepseek --key sk-...
ccs use deepseek
```

仓库：https://github.com/Ike-li/ccs
对比说明：https://github.com/Ike-li/ccs/blob/main/docs/compare.md
~~~

### 掘金

标题：

```text
ccs：一个不做代理的 Claude Code provider 切换小工具
```

摘要：

```text
ccs 是一个 POSIX shell CLI，用来在 DeepSeek、OpenRouter、Kimi、Hugging Face、LiteLLM/企业网关等 Anthropic-compatible endpoint 之间切换 Claude Code 配置。
```

正文结构：

~~~markdown
## 背景

Claude Code 支持通过 `~/.claude/settings.json` 里的 `ANTHROPIC_BASE_URL`、`ANTHROPIC_API_KEY`、`ANTHROPIC_AUTH_TOKEN` 接入 Anthropic-compatible endpoint。但频繁手改 JSON、切换 API key / bearer token、排查 shell 里残留的 secret 变量，很容易出错。

## ccs 做什么

`ccs` 只做一件事：管理多个 Claude Code provider，并把当前 active provider 写进 Claude Code 官方支持的 settings 文件。

它不做：
- 本地代理
- 协议转换
- 请求转发
- 密钥托管

## 快速开始

```bash
brew install Ike-li/tap/ccs
ccs init
ccs preset deepseek --key sk-...
ccs use deepseek
```

## 为什么不是 proxy

如果你的上游只支持 OpenAI/Gemini/Ollama 协议，应该用 LiteLLM 或其他 router/gateway 先转成 Anthropic-compatible endpoint。`ccs` 只负责 Claude Code 客户端侧切换，避免多一层本地常驻进程。

## 诊断能力

`ccs doctor` 会检查：
- Claude Code / curl 是否在 PATH
- settings 文件是否可读写
- active provider 是否存在
- key / base URL 是否完整
- 当前 shell 是否残留了另一种 secret

## 链接

GitHub：https://github.com/Ike-li/ccs
对比文档：https://github.com/Ike-li/ccs/blob/main/docs/compare.md
~~~

### 少数派

选题角度：

```text
我如何把 Claude Code 多 provider 切换从手改 JSON 变成一个命令
```

开头：

```markdown
这不是一个“让 Claude Code 支持所有模型”的工具。相反，它把边界收得很窄：当一个服务已经提供 Anthropic-compatible endpoint 时，`ccs` 只负责把 Claude Code 的当前 provider 切过去。

这个小工具来自一个很具体的痛点：我在 DeepSeek、OpenRouter、Kimi、LiteLLM/企业网关之间切换 Claude Code 时，不想反复手改 `~/.claude/settings.json`，也不想因为 `ANTHROPIC_API_KEY` 和 `ANTHROPIC_AUTH_TOKEN` 同时存在而排查半天。
```

正文要点：

- 为什么 Claude Code provider 切换容易出错。
- 为什么 `ccs` 不做 proxy，而是只写官方 settings。
- Homebrew 安装和 `ccs preset deepseek/openrouter`。
- `ccs doctor` 如何帮助定位 API key / auth token 冲突。
- 明文 secret 边界：provider 文件和 settings.json 都应按敏感文件对待。

结尾：

~~~markdown
如果你也在 Claude Code 里切多个 Anthropic-compatible provider，可以试试：

```bash
brew install Ike-li/tap/ccs
ccs init
ccs preset deepseek --key sk-...
ccs use deepseek
```

项目地址：https://github.com/Ike-li/ccs
~~~

## Maintainer reminders

- Keep README first screen focused on the switching problem, not on every command.
- Keep provider docs factual and source-aligned; provider defaults age quickly.
- Do not bury the plaintext secret boundary.
- When adding a new preset, update README, `docs/providers.md`, tests, and this outreach file if the provider becomes a headline use case.
