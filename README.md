# ccs

[![CI](https://github.com/Ike-li/ccs/actions/workflows/test.yml/badge.svg)](https://github.com/Ike-li/ccs/actions/workflows/test.yml)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Shell](https://img.shields.io/badge/runtime-POSIX%20sh-2f7d32.svg)](bin/ccs)

Claude Code provider 切换工具。`ccs use <name>` 会把当前 provider 的 `ANTHROPIC_BASE_URL` 和对应 secret 写进 `~/.claude/settings.json`：

- 默认写 `ANTHROPIC_API_KEY`
- token provider 写 `ANTHROPIC_AUTH_TOKEN`

这是一个纯 shell 版本，运行时不依赖 Python、Node、jq 或 daemon。macOS 和常见 Linux 发行版自带的 `/bin/sh`、`awk`、`sed`、`stty` 即可运行；只有 `ccs verify` / 默认 `ccs use` 验证请求需要 `curl`。

## 功能

- `ccs set` 逐项填写 provider：name、base URL、secret env、key、默认模型和 `/model` alias 映射
- `ccs set <name> ...` 支持脚本式创建或更新
- `ccs use <name>` 写入 Claude Code 的 `settings.json`
- API key / auth token 二选一，切换时自动清理另一种 secret env
- provider 配置保存在 `~/.config/ccs/providers/<name>.conf`
- `ccs ls` / `ccs current` / `ccs show` 查看配置
- `ccs verify [name]` 发送一次 Anthropic messages 探测请求

## 安装

本地仓库内直接安装：

```bash
mkdir -p ~/.local/bin
install -m 755 bin/ccs ~/.local/bin/ccs
```

确保 `~/.local/bin` 在 `PATH` 里：

```bash
ccs --help
```

也可以不安装，直接在仓库里运行：

```bash
./bin/ccs --help
```

## 如何使用

初始化配置目录：

```bash
ccs init
```

交互式添加 provider：

```bash
ccs set kimi
```

它会逐项询问：

```text
Base URL [https://api.moonshot.cn/anthropic]:
Secret env (<-/->, Enter): ANTHROPIC_API_KEY  ANTHROPIC_AUTH_TOKEN
Key for ANTHROPIC_API_KEY:
Model (optional):
Opus model (optional):
Sonnet model (optional):
Haiku model (optional):
```

在支持 TTY 的终端里，`Secret env` 可以用左右方向键选择，当前项会显示为颜色块。大多数 provider 直接选 `ANTHROPIC_API_KEY`；需要 Bearer token 的 provider 选 `ANTHROPIC_AUTH_TOKEN`。key/token 只填一次。

`Model` 写入 `ANTHROPIC_MODEL`，控制 Claude Code 启动时的会话默认模型。`Opus model`、`Sonnet model`、`Haiku model` 写入 `/model` 里 `opus`、`sonnet`、`haiku` alias 的默认映射。单模型 provider 可以先填 `Model`，后面三个一路回车；支持多模型的 provider 可以分别填写。

切换 provider：

```bash
ccs use kimi
```

`ccs use` 默认会先调用 `ccs verify`。如果只是本地切换、不想发请求：

```bash
ccs use kimi --no-verify
```

切换后重启 Claude Code 会话，让新 settings 生效。

如果 Claude Code 提示 `Auth conflict: Both a token ... and an API key ... are set`，通常是当前 shell 里还 export 着另一种 secret，而不是 `settings.json` 写错。普通 `ccs use` 是子进程，不能直接 unset 父 shell；它会提示你需要执行的 cleanup，例如：

```bash
unset ANTHROPIC_AUTH_TOKEN
claude
```

需要一次性清理所有 ccs 管理的 `ANTHROPIC_*` 变量时，可以用 `eval "$(ccs use kimi --shell)"`。`--shell` 会照常写入 `settings.json`，并把需要执行的 `unset ...` 输出到 stdout；普通切换日志会写到 stderr，方便 `eval` 安全执行。也可以直接开一个新终端再启动 Claude Code。

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
ccs set kimi \
  --base-url https://api.moonshot.cn/anthropic \
  --key sk-... \
  --use-auth-token \
  --model kimi-k2.6 \
  --opus-model kimi-k2.6 \
  --sonnet-model kimi-k2.6 \
  --haiku-model kimi-k2.6
```

不想让 key 出现在 shell history，可以从 stdin 读取：

```bash
printf '%s\n' 'sk-...' | ccs set kimi \
  --base-url https://api.moonshot.cn/anthropic \
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
