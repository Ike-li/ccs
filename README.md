# ccs-py

[![CI](https://github.com/Ike-li/ccs/actions/workflows/test.yml/badge.svg)](https://github.com/Ike-li/ccs/actions/workflows/test.yml)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

Python 版 Claude Code provider 切换工具。安装后命令名是 `ccs-py`，它会把当前 provider 的 `ANTHROPIC_BASE_URL` 和对应 secret 写进 `~/.claude/settings.json`：

- 默认写 `ANTHROPIC_API_KEY`
- token provider 写 `ANTHROPIC_AUTH_TOKEN`

`py` 分支只维护 Python 版本；shell 版本在 `main` 分支。两个分支共用同一套运行数据格式：`~/.config/ccs/providers/<name>.conf` 和 `~/.config/ccs/active`。

## 功能

- `ccs-py set` 逐项填写 provider：name、base URL、secret env、key、model
- `ccs-py set <name> ...` 支持脚本式创建或更新
- `ccs-py use <name>` 写入 Claude Code 的 `settings.json`
- API key / auth token 二选一，切换时自动清理另一种 secret env
- `ccs-py ls` / `ccs-py current` / `ccs-py show` 查看配置
- `ccs-py verify [name]` 发送一次 Anthropic messages 探测请求

## 安装

```bash
uv tool install .
# 或
pipx install .
```

验证：

```bash
ccs-py --help
```

## 如何使用

初始化配置目录：

```bash
ccs-py init
```

交互式添加 provider：

```bash
ccs-py set kimi
```

它会逐项询问：

```text
Base URL [https://api.moonshot.cn/anthropic]:
Secret env (<-/->, Enter): ANTHROPIC_API_KEY  ANTHROPIC_AUTH_TOKEN
Key for ANTHROPIC_API_KEY:
Model (optional):
```

在支持 TTY 的终端里，`Secret env` 可以用左右方向键选择，当前项会显示为颜色块。大多数 provider 直接选 `ANTHROPIC_API_KEY`；需要 Bearer token 的 provider 选 `ANTHROPIC_AUTH_TOKEN`。key/token 只填一次。

切换 provider：

```bash
ccs-py use kimi
```

`use` 默认会先调用 `verify`。如果只是本地切换、不想发请求：

```bash
ccs-py use kimi --no-verify
```

切换后重启 Claude Code 会话，让新 settings 生效。

## 常用命令

| 命令 | 用途 |
|---|---|
| `ccs-py init` | 创建 `~/.config/ccs` |
| `ccs-py set [name]` | 交互式创建或更新 provider |
| `ccs-py set <name> --base-url URL --key KEY` | 脚本式创建或更新 provider |
| `ccs-py set <name> --use-auth-token` | 把 secret 写到 `ANTHROPIC_AUTH_TOKEN` |
| `ccs-py use <name>` | 切换 active provider，默认先 verify |
| `ccs-py use <name> --no-verify` | 跳过 verify 直接切换 |
| `ccs-py verify [name]` | 单独验证 provider |
| `ccs-py ls` | 列出 providers |
| `ccs-py current` | 显示 active provider |
| `ccs-py show <name> [--show-key]` | 显示 provider，默认脱敏 key |
| `ccs-py rm <name>` | 删除 provider；如果删的是 active，会清理 settings |

高级参数：

```bash
ccs-py set <name> --model claude-sonnet-4-6
ccs-py set <name> --unset-model
ccs-py set <name> -e ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-4-6
ccs-py set <name> --unset-env ANTHROPIC_DEFAULT_SONNET_MODEL
```

## 脚本用法

API key provider：

```bash
ccs-py set anthropic \
  --base-url https://api.anthropic.com \
  --key sk-ant-... \
  --use-api-key
```

Auth token provider：

```bash
ccs-py set kimi \
  --base-url https://api.moonshot.cn/anthropic \
  --key sk-... \
  --use-auth-token
```

不想让 key 出现在 shell history，可以从 stdin 读取：

```bash
printf '%s\n' 'sk-...' | ccs-py set kimi \
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
```

provider 文件是简单的 `KEY=value`：

```text
auth=api_key
key=sk-...
ANTHROPIC_BASE_URL=https://api.example.com/anthropic
ANTHROPIC_MODEL=claude-sonnet-4-6
```

`ccs-py` 写入 settings 时会移除它管理的 `ANTHROPIC_*` 变量和旧的 `apiKeyHelper`，再写入当前 provider；其他顶层字段和非 ccs 管理的 `env` 会保留。

## Verify

`verify` 会向 `${ANTHROPIC_BASE_URL}/v1/messages` 发送一次 `max_tokens=1` 的探测请求，用来提前发现：

- 401 / 403
- 模型名错误
- base URL 不通或超时

`CCS_VERIFY_TIMEOUT` 可以调整超时秒数，默认 10 秒。

## 安全语义

- `~/.config/ccs/providers/*.conf` 包含 provider 明文 key
- `~/.claude/settings.json` 包含当前 active provider 的明文 key
- 配置文件会尽量设置为 `0600`，配置目录为 `0700`
- 如果 settings.json 会同步到云端或被备份，请按明文 secret 文件对待

## 完全卸载

```bash
uv tool uninstall ccs
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
