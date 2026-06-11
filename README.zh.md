# ccs: Claude Code provider switcher

[English](README.md) | 简体中文

[![CI](https://github.com/Ike-li/ccs/actions/workflows/test.yml/badge.svg)](https://github.com/Ike-li/ccs/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/Ike-li/ccs?sort=semver)](https://github.com/Ike-li/ccs/releases)
[![Homebrew](https://img.shields.io/badge/install-Homebrew-fbb040.svg)](#安装)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Shell](https://img.shields.io/badge/runtime-POSIX%20sh-2f7d32.svg)](bin/ccs)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-provider%20switcher-6b5cff.svg)](docs/compare.md)

Switch Claude Code between Anthropic-compatible providers in seconds. No proxy. No daemon. No Node runtime.

`ccs` 是一个极小的 Claude Code provider switcher。它管理多个 Anthropic-compatible endpoints，并把当前 provider 的 `ANTHROPIC_BASE_URL` 和对应 secret 写进 Claude Code 官方支持的 `~/.claude/settings.json`：

- API key provider 写 `ANTHROPIC_API_KEY`
- Bearer token provider 写 `ANTHROPIC_AUTH_TOKEN`

适合：Anthropic-compatible endpoint、LiteLLM/企业网关、OpenRouter、DeepSeek、Kimi 等已经能直接接 Claude Code 的场景。不适合：把 OpenAI/Gemini/Ollama 协议转换成 Anthropic Messages API；那是 router/gateway 的工作。

<sub>Search terms: Claude Code provider switcher, Anthropic-compatible endpoint manager, OpenRouter / DeepSeek / Kimi / LiteLLM setup helper, API key and auth token conflict doctor.</sub>

## 30 秒判断

| 如果你正在... | `ccs` 帮你... |
|---|---|
| 在多个 Claude Code provider 之间切换 | 用 `ccs use <name>` 改 active provider，不反复手改 JSON |
| 配 DeepSeek、OpenRouter、Kimi 或企业网关 | 用 preset / recipe 固化 base URL、auth mode 和模型 alias |
| 遇到 API key 和 auth token 冲突 | 用 `ccs doctor` 找出 settings 和当前 shell 的冲突来源 |
| 想避免本地代理和额外运行时 | 只用 POSIX `sh` 写官方 `settings.json`，不启动 daemon |
| 想给团队复用配置路径 | 用可复制命令、Homebrew 安装和明确定义的 provider 文件布局 |

## 60 秒上手

推荐通过 Homebrew 安装：

```bash
brew install Ike-li/tap/ccs
ccs init
ccs preset deepseek --key sk-...
ccs use deepseek
```

![ccs terminal demo](docs/demo.gif)

切换后重启 Claude Code 会话，让新 settings 生效。

不用 Homebrew 时，也可以用安装脚本。它是次选路径；脚本默认锁定发布 tag 并校验 `bin/ccs` 的 sha256，覆盖 `CCS_INSTALL_REF` 时也应同时覆盖 `CCS_INSTALL_SHA256`：

```bash
curl -fsSL https://raw.githubusercontent.com/Ike-li/ccs/main/install.sh | sh
```

## 使用场景

- 在 Anthropic、DeepSeek、OpenRouter、Kimi、Hugging Face 或企业 Anthropic-compatible gateway 之间切换。
- 给 LiteLLM / 内部网关用户提供一个不改变上游架构的 Claude Code 配置入口。
- 把 provider recipe 写进 README、runbook 或 onboarding 文档，让新成员少踩 auth mode 和 model alias 的坑。
- 用 `ccs doctor` 检查 Claude Code 是否能读到当前 settings、是否有 secret 冲突、active provider 是否完整。
- 在不引入 Node/Python runtime、不运行本地 proxy 的前提下，保持配置可审计、可复制、可删除。

## 和其他方式比

| 方式 | 适合 | 主要代价 | `ccs` 的定位 |
|---|---|---|---|
| 手改 `~/.claude/settings.json` | 一次性实验 | 容易写错 env、残留旧 key、难复现 | 把切换动作变成命令和 provider 文件 |
| `export ANTHROPIC_*` 脚本 | 临时 shell 会话 | 容易和 settings 互相冲突，换终端就丢 | 写入 Claude Code 官方 settings，并提示 shell cleanup |
| 本地 proxy / router | 协议转换、多模型路由 | 需要常驻进程、端口、更多配置 | 不代理请求，只切换已兼容 Claude Code 的 endpoint |
| 密钥管理器 / `.env` 工具 | 加密和团队密钥治理 | 不负责 Claude Code provider 语义 | 保持轻量；明文边界写清楚，必要时可和密钥流程搭配 |

更完整的取舍见 [docs/compare.md](docs/compare.md)。

## 功能

- `ccs set` 逐项填写 provider：name、base URL、secret env、key、默认模型、`/model` alias 和 Claude Code 子 agent env
- `ccs set <name> ...` 支持脚本式创建或更新
- `ccs preset <deepseek|openrouter>` 用内置 recipe 快速创建常见 provider
- `ccs use <name>` 写入 Claude Code 的 `settings.json`
- API key / auth token 二选一，切换时自动清理另一种 secret env
- provider 配置保存在 `~/.config/ccs/providers/<name>.conf`
- `ccs ls` / `ccs current` / `ccs show` 查看配置
- `ccs verify [name]` 发送一次 Anthropic messages 探测请求
- `ccs doctor` 检查本机 Claude Code / settings / provider / shell secret 状态

## 安装

推荐通过 Homebrew 安装：

```bash
brew install Ike-li/tap/ccs
```

不用 Homebrew 时，可以一行安装到 `~/.local/bin`。这条 `curl | sh` 路径不如 Homebrew 易审计，适合一次性安装或自动化环境；安装脚本会校验下载内容的 sha256：

```bash
curl -fsSL https://raw.githubusercontent.com/Ike-li/ccs/main/install.sh | sh
```

确保 `~/.local/bin` 在 `PATH` 里：

```bash
ccs --help
```

本地仓库内安装：

```bash
mkdir -p ~/.local/bin
install -m 755 bin/ccs ~/.local/bin/ccs
```

也可以不安装，直接在仓库里运行：

```bash
./bin/ccs --help
```

发布和 Homebrew tap 维护见 [docs/releasing.md](docs/releasing.md)。

### Shell 补全（可选）

仓库 `completions/` 目录提供 bash 和 zsh 的补全脚本，可以 tab 补全子命令、provider name、`--*` 选项。

bash：
```bash
. /path/to/ccs/completions/ccs.bash   # 加进 ~/.bashrc
```

zsh：
```bash
mkdir -p ~/.zsh/completions
cp completions/_ccs ~/.zsh/completions/_ccs
# 在 ~/.zshrc 加入：
#   fpath=(~/.zsh/completions $fpath)
#   autoload -Uz compinit && compinit
```

## 如何使用

初始化配置目录：

```bash
ccs init
```

交互式添加 provider：

```bash
ccs set deepseek
```

它会逐项询问：

```text
Base URL:
Secret env (<-/->, Enter): ANTHROPIC_API_KEY  ANTHROPIC_AUTH_TOKEN
Key for ANTHROPIC_AUTH_TOKEN:
Model (optional):
Opus model (optional):
Sonnet model (optional):
Haiku model (optional):
```

在支持 TTY 的终端里，`Secret env` 可以用左右方向键选择，当前项会显示为颜色块。大多数 provider 直接选 `ANTHROPIC_API_KEY`；需要 Bearer token 的 provider 选 `ANTHROPIC_AUTH_TOKEN`。key/token 只填一次。

`Model` 写入 `ANTHROPIC_MODEL`，控制 Claude Code 启动时的会话默认模型。`Opus model`、`Sonnet model`、`Haiku model` 写入 `/model` 里 `opus`、`sonnet`、`haiku` alias 的默认映射。单模型 provider 可以先填 `Model`，后面三个一路回车；支持多模型的 provider 可以分别填写。

切换 provider：

```bash
ccs use deepseek
```

`ccs use` 默认会先调用 `ccs verify`。如果只是本地切换、不想发请求：

```bash
ccs use deepseek --no-verify
```

切换后重启 Claude Code 会话，让新 settings 生效。

如果 Claude Code 提示 `Auth conflict: Both a token ... and an API key ... are set`，通常是当前 shell 里还 export 着另一种 secret，而不是 `settings.json` 写错。普通 `ccs use` 是子进程，不能直接 unset 父 shell；它会提示你需要执行的 cleanup，例如：

```bash
unset ANTHROPIC_AUTH_TOKEN
claude
```

需要一次性清理所有 ccs 管理的 provider env 时，可以用 `eval "$(ccs use deepseek --shell)"`。`--shell` 会照常写入 `settings.json`，并把需要执行的 `unset ...` 输出到 stdout；普通切换日志会写到 stderr，方便 `eval` 安全执行。也可以直接开一个新终端再启动 Claude Code。

### 切回 claude.ai 订阅

`official` 是内置伪 provider：执行后把 ccs 托管的 provider env 从 `settings.json` 中移除，Claude Code 会回落到自己的 claude.ai 登录（OAuth）：

```bash
ccs use official
```

如果还没登录过，在 Claude Code 里执行一次 `/login`；切回三方 provider 直接 `ccs use <name>`。如果当前 shell 还 export 着 `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN`，它们会压过订阅登录——`ccs use official` 会给出警告，也可以用 `eval "$(ccs use official --shell)"` 一并清理。

### 项目级 provider 固定

`--project` 把 provider 固定到当前目录：托管 env 写入 `./.claude/settings.local.json`。Claude Code 会把这份文件按键合并到全局 settings 之上，所以这个目录里 pin 生效，文件里其余内容（permissions、hooks、非托管 env）原样保留并继续继承全局：

```bash
ccs use glm --project          # 这个目录用 glm
ccs use official --project     # 这个目录用 claude.ai 订阅
ccs use --global               # 移除 pin，回归全局 settings
```

安全护栏：

- 项目文件未被 git ignore 时，ccs 拒绝把 secret 写进去，并给出一行修复命令。
- 全局 settings 里有、而被 pin 的 provider 没定义的托管键会被写成 `""`，挡住按键合并的渗透（Claude Code 把空 env 值当作未设置）。`ccs use official --project` 同样用空串覆盖认证/URL/模型核心键。
- 在已 pin 的目录里 `ccs current` 显示项目/全局两行（pin 会反查回 provider 名）；`ccs doctor` 会报告渗透键和 gitignore 问题。

项目 pin 不会动全局 active 指针；env 变更同样需要重启 Claude Code 会话才生效。

### 给手工复制的项目文件瘦身

项目文件往往是从全局 settings 手工复制出来的，大多数非 env 键和全局逐字节相同——它们会永远遮住全局作用域（重复配置的 hook 甚至会跑两遍）。`ccs slim` 报告这些重复键；`ccs slim --apply` 先备份到 `~/.config/ccs/backups/` 再删除它们，之后这些键自动从全局继承——有效配置完全不变，而且以后改全局、项目自动跟：

```bash
ccs slim            # 报告与全局重复的顶层键
ccs slim --apply    # 删除（保留备份；需要 jq）
```

与全局值不同的键永远保留，`env` 块永不触碰。

## 常用命令

| 命令 | 用途 |
|---|---|
| `ccs init` | 创建 `~/.config/ccs` |
| `ccs set [name]` | 交互式创建或更新 provider |
| `ccs set <name> --base-url URL --key KEY` | 脚本式创建或更新 provider |
| `ccs set <name> --use-auth-token` | 把 secret 写到 `ANTHROPIC_AUTH_TOKEN` |
| `ccs preset deepseek --key KEY` | 用内置 DeepSeek recipe 创建 provider |
| `ccs preset openrouter --key KEY` | 用内置 OpenRouter recipe 创建 provider |
| `ccs use <name>` | 切换 active provider，默认先 verify |
| `ccs use <name> --no-verify` | 跳过 verify 直接切换 |
| `ccs use official` | 切回 claude.ai 订阅（清除托管 provider env） |
| `ccs use <name> --project` | 为当前目录固定 provider（写 `./.claude/settings.local.json`） |
| `ccs use official --project` | 当前目录固定使用 claude.ai 订阅 |
| `ccs use --global` | 移除项目 pin，目录回归全局 settings |
| `ccs slim [--apply]` | 报告/删除项目里与全局重复的顶层键 |
| `ccs verify [name]` | 单独验证 provider |
| `ccs doctor` | 本地诊断 settings、active provider、依赖和 shell secret 冲突 |
| `ccs ls` | 列出 providers |
| `ccs current` | 显示 active provider |
| `ccs show <name> [--show-key]` | 显示 provider，默认脱敏 key |
| `ccs rm <name>` | 删除 provider；如果删的是 active，会清理 settings |

高级参数：

```bash
ccs set <name> --model claude-sonnet-4-6
ccs set <name> --opus-model claude-opus-4-7
ccs set <name> --sonnet-model claude-sonnet-4-6
ccs set <name> --haiku-model claude-haiku-4-5
ccs set <name> --unset-model
ccs set <name> -e ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-4-6
ccs set <name> -e CLAUDE_CODE_SUBAGENT_MODEL=claude-haiku-4-5
ccs set <name> -e CLAUDE_CODE_EFFORT_LEVEL=max
ccs set <name> --unset-env ANTHROPIC_DEFAULT_SONNET_MODEL
```

`--unset-model` 只清理 `ANTHROPIC_MODEL`。如果要清理 Opus/Sonnet/Haiku alias、Claude Code subagent model 或 effort level，继续用 `--unset-env KEY`，这样高级模型元数据变量也保持同一套清理方式。

## 脚本用法

API key provider：

```bash
ccs set anthropic \
  --base-url https://api.anthropic.com \
  --key sk-ant-... \
  --use-api-key
```

Auth token provider：

```bash
ccs set openrouter \
  --base-url https://openrouter.ai/api \
  --key sk-or-v1-... \
  --use-auth-token \
  --opus-model '~anthropic/claude-opus-latest' \
  --sonnet-model '~anthropic/claude-sonnet-latest' \
  --haiku-model '~anthropic/claude-haiku-latest' \
  -e CLAUDE_CODE_SUBAGENT_MODEL='~anthropic/claude-opus-latest'
```

DeepSeek 的 Claude Code 接入文档使用 `ANTHROPIC_AUTH_TOKEN` / Bearer auth。`ccs set` 遇到官方 Anthropic 兼容地址会默认选 auth token；如果已有旧配置写成了 API key 模式，可以这样切换：

```bash
ccs set ds --use-auth-token
ccs use ds
```

更多 provider 配方见 [docs/providers.md](docs/providers.md)。

常见 provider 可以直接用 preset：

```bash
ccs preset deepseek --key sk-...
ccs preset openrouter --key sk-or-v1-...
```

不想让 key 出现在 shell history，可以从 stdin 读取：

```bash
printf '%s\n' 'sk-or-v1-...' | ccs set openrouter \
  --base-url https://openrouter.ai/api \
  --key - \
  --use-auth-token
```

## 文件布局

```text
~/.config/ccs/
  active
  providers/
    kimi.conf

~/.claude/settings.json
  env:
    ANTHROPIC_BASE_URL:    ...
    ANTHROPIC_API_KEY:     ...  # API key 模式
    ANTHROPIC_AUTH_TOKEN:  ...  # auth token 模式
    ANTHROPIC_MODEL:       ...  # 可选
    ANTHROPIC_DEFAULT_OPUS_MODEL:    ...  # 可选，/model opus alias
    ANTHROPIC_DEFAULT_SONNET_MODEL:  ...  # 可选，/model sonnet alias
    ANTHROPIC_DEFAULT_HAIKU_MODEL:   ...  # 可选，/model haiku alias
    CLAUDE_CODE_SUBAGENT_MODEL:      ...  # 可选，子 agent 模型
    CLAUDE_CODE_EFFORT_LEVEL:        ...  # 可选，provider 建议的 effort level
```

provider 文件是简单的 `KEY=value`：

```text
auth=api_key
key=sk-...
ANTHROPIC_BASE_URL=https://api.example.com/anthropic
ANTHROPIC_MODEL=claude-sonnet-4-6
ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-7
ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-4-6
ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku-4-5
CLAUDE_CODE_SUBAGENT_MODEL=claude-haiku-4-5
```

`ccs` 写入 settings 时会移除它管理的 provider env 和旧的 `apiKeyHelper`，再写入当前 provider；其他顶层字段和非 ccs 管理的 `env` 会保留。
如果本机有 `jq`，`ccs` 会用它重新序列化 settings，尽量保持嵌套字段可读；没有 `jq` 时会回退到内置 POSIX awk 写入器，非 `env` 顶层字段会被压缩成单行但语义保持不变。

## Verify

`ccs verify` 会向 `${ANTHROPIC_BASE_URL}/v1/messages` 发送一次 `max_tokens=1` 的探测请求，用来提前发现：

- 401 / 403
- 模型名错误
- base URL 不通或超时

`CCS_VERIFY_TIMEOUT` 可以调整超时秒数，默认 10 秒。

探测模型优先使用 `ANTHROPIC_MODEL`，如果没配置，会依次使用 `ANTHROPIC_DEFAULT_OPUS_MODEL`、`ANTHROPIC_DEFAULT_SONNET_MODEL`、`ANTHROPIC_DEFAULT_HAIKU_MODEL`，最后才回退到内置 probe model。

## Doctor

`ccs doctor` 做本地诊断，不会发网络请求：

- `claude` / `curl` 是否在 `PATH`
- `~/.config/ccs` 和 provider 数量
- `~/.claude/settings.json` 是否可读写
- active provider 是否存在、是否有 key 和 base URL
- 当前 shell 是否 export 了另一种 secret
- DeepSeek provider 是否仍在使用 API key 模式

```bash
ccs doctor
```

正常配置后大致会看到：

```text
ccs doctor 0.7.0
ok:   config dir exists: ~/.config/ccs
ok:   providers configured: 1
ok:   claude command found
ok:   curl command found
ok:   settings file exists: ~/.claude/settings.json
ok:   settings file is readable
ok:   settings file is writable
ok:   active provider: deepseek
ok:   active provider key is set: <len=8>
ok:   active provider base URL: https://api.deepseek.com/anthropic
ok:   active provider secret env: ANTHROPIC_AUTH_TOKEN
summary: 0 failure(s), 0 warning(s)
```

## 故障排查

| `ccs verify` 输出 | 含义 | 建议处理 |
|---|---|---|
| `Authentication failed (401)` | provider key 错或失效 | `ccs show <name> --show-key` 核对；用 `ccs set <name> --key NEW` 更新 |
| `Access denied (403)` | key 有效但被拒绝（账号/权限/IP 限制） | 登录 provider 控制台检查 key 的 scope / 配额 / IP 白名单 |
| `Provider rejected: <message>` | provider 主动拒绝（model 错、key 没权限、参数无效等） | 看 message 内容；如果是模型不存在，用 `ccs set <name> --model <provider 支持的模型>` 显式指定，或 `--opus-model` / `--sonnet-model` / `--haiku-model` 单独映射 |
| `Connection failed: ...` | base URL 不通、DNS 解析失败、超时 | 用 `curl -v ${BASE_URL}/v1/messages` 验证可达；调整 `CCS_VERIFY_TIMEOUT` |
| `unsupported scheme: file` | base URL 不是 http(s) | `ccs set <name> --base-url https://...` |

Claude Code 启动时如果报 `Auth conflict: Both a token ... and an API key ... are set`，看本文上半部分"切换 provider"段落，按提示 unset 当前 shell 里残留的 secret 变量。

## 安全语义

- `~/.config/ccs/providers/*.conf` 包含 provider 明文 key
- `~/.claude/settings.json` 包含当前 active provider 的明文 key
- 配置文件会尽量设置为 `0600`，配置目录为 `0700`
- 如果 settings.json 会同步到云端或被备份，请按明文 secret 文件对待

## 项目维护

- 版本变化见 [CHANGELOG.md](CHANGELOG.md)
- 和手改 settings、shell export、本地 proxy 的对比见 [docs/compare.md](docs/compare.md)
- 贡献说明见 [CONTRIBUTING.md](CONTRIBUTING.md)
- 安全边界和漏洞报告见 [SECURITY.md](SECURITY.md)
- 传播文案和 awesome-list pitch 见 [docs/outreach.md](docs/outreach.md)

## 完全卸载

```bash
rm -f ~/.local/bin/ccs
rm -rf ~/.config/ccs
# 可选：清理 ~/.claude/settings.json 里的 ANTHROPIC_* env
```

## 退出码

| 码 | 说明 |
|---|---|
| 0 | 成功 |
| 1 | 用户错误、verify 失败、输入无效 |

## License

GPL-3.0 - see [LICENSE](LICENSE).
