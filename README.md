# ccs

[![CI](https://github.com/Ike-li/ccs/actions/workflows/test.yml/badge.svg)](https://github.com/Ike-li/ccs/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/Ike-li/ccs?sort=semver)](https://github.com/Ike-li/ccs/releases)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Shell](https://img.shields.io/badge/runtime-POSIX%20sh-2f7d32.svg)](bin/ccs)

No proxy. No daemon. No Node. Just switch Claude Code providers safely.

`ccs` 是一个极小的 Claude Code provider 切换工具。它不做协议转换、不启动本地代理，只负责把当前 provider 的 `ANTHROPIC_BASE_URL` 和对应 secret 写进 Claude Code 官方支持的 `~/.claude/settings.json`：

- API key provider 写 `ANTHROPIC_API_KEY`
- Bearer token provider 写 `ANTHROPIC_AUTH_TOKEN`

适合：Anthropic-compatible endpoint、LiteLLM/企业网关、OpenRouter、DeepSeek、Kimi 等已经能直接接 Claude Code 的场景。

不适合：把 OpenAI/Gemini/Ollama 协议转换成 Anthropic Messages API。那是 router/gateway 的工作，不是 `ccs` 的工作。

这是一个纯 shell 版本，运行时不依赖 Python、Node、jq 或 daemon。macOS 和常见 Linux 发行版自带的 `/bin/sh`、`awk`、`sed`、`stty` 即可运行；只有一行安装和 `ccs verify` / 默认 `ccs use` 验证请求需要 `curl`。

## 60 秒上手

```bash
brew install Ike-li/tap/ccs
ccs init
ccs set deepseek \
  --base-url https://api.deepseek.com/anthropic \
  --key sk-... \
  --model 'deepseek-v4-pro[1m]' \
  --haiku-model deepseek-v4-flash
ccs use deepseek
```

切换后重启 Claude Code 会话，让新 settings 生效。

不用 Homebrew 时，也可以用安装脚本：

```bash
CCS_INSTALL_REF=v0.5.0 sh -c "$(curl -fsSL https://raw.githubusercontent.com/Ike-li/ccs/main/install.sh)"
```

## 功能

- `ccs set` 逐项填写 provider：name、base URL、secret env、key、默认模型和 `/model` alias 映射
- `ccs set <name> ...` 支持脚本式创建或更新
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

不用 Homebrew 时，可以一行安装到 `~/.local/bin`：

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

需要一次性清理所有 ccs 管理的 `ANTHROPIC_*` 变量时，可以用 `eval "$(ccs use deepseek --shell)"`。`--shell` 会照常写入 `settings.json`，并把需要执行的 `unset ...` 输出到 stdout；普通切换日志会写到 stderr，方便 `eval` 安全执行。也可以直接开一个新终端再启动 Claude Code。

## 常用命令

| 命令 | 用途 |
|---|---|
| `ccs init` | 创建 `~/.config/ccs` |
| `ccs set [name]` | 交互式创建或更新 provider |
| `ccs set <name> --base-url URL --key KEY` | 脚本式创建或更新 provider |
| `ccs set <name> --use-auth-token` | 把 secret 写到 `ANTHROPIC_AUTH_TOKEN` |
| `ccs use <name>` | 切换 active provider，默认先 verify |
| `ccs use <name> --no-verify` | 跳过 verify 直接切换 |
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
ccs set <name> --unset-env ANTHROPIC_DEFAULT_SONNET_MODEL
```

`--unset-model` 只清理 `ANTHROPIC_MODEL`。如果要清理 Opus/Sonnet/Haiku alias 映射，继续用 `--unset-env ANTHROPIC_DEFAULT_*_MODEL`，这样高级模型元数据变量也保持同一套清理方式。

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
  --haiku-model '~anthropic/claude-haiku-latest'
```

DeepSeek 的 Claude Code 接入文档使用 `ANTHROPIC_AUTH_TOKEN` / Bearer auth。`ccs set` 遇到官方 Anthropic 兼容地址会默认选 auth token；如果已有旧配置写成了 API key 模式，可以这样切换：

```bash
ccs set ds --use-auth-token
ccs use ds
```

更多 provider 配方见 [docs/providers.md](docs/providers.md)。

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
```

`ccs` 写入 settings 时会移除它管理的 `ANTHROPIC_*` 变量和旧的 `apiKeyHelper`，再写入当前 provider；其他顶层字段和非 ccs 管理的 `env` 会保留。

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

GPL-3.0 — see [LICENSE](LICENSE).
