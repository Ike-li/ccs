"""End-to-end tests for the shell-based ccs CLI."""

import json
import os
import pty
import re
import select
import stat
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CCS = ROOT / "bin" / "ccs"
INSTALL = ROOT / "install.sh"


def run(
    home: Path, *args: str, input_text: str | None = None, check: bool = True, env_extra: dict[str, str] | None = None
):
    env = {**os.environ, "HOME": str(home), "CCS_VERIFY_TIMEOUT": "1"}
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    env.pop("CCS_DIR", None)
    env.pop("CLAUDE_SETTINGS_FILE", None)
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        [str(CCS), *args],
        input=input_text,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"ccs {' '.join(args)} failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


def settings(home: Path) -> dict:
    return json.loads((home / ".claude/settings.json").read_text())


def provider_conf(home: Path, name: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in (home / f".config/ccs/providers/{name}.conf").read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key] = value
    return data


def provider_env_keys() -> list[str]:
    script = CCS.read_text()
    match = re.search(r'^PROVIDER_ENV_KEYS="([^"]+)"$', script, re.MULTILINE)
    assert match is not None
    return match.group(1).split()


def write_fake_curl(fake_bin: Path, log_file: Path) -> None:
    fake_bin.mkdir(exist_ok=True)
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        """#!/bin/sh
out=
config=
while [ "$#" -gt 0 ]; do
    printf 'ARG:%s\\n' "$1" >> "$CCS_FAKE_CURL_LOG"
    case "$1" in
        -o)
            out=$2
            printf 'ARG:%s\\n' "$2" >> "$CCS_FAKE_CURL_LOG"
            shift 2
            ;;
        --config)
            config=$2
            printf 'ARG:%s\\n' "$2" >> "$CCS_FAKE_CURL_LOG"
            shift 2
            ;;
        --data)
            printf 'DATA:%s\\n' "$2" >> "$CCS_FAKE_CURL_LOG"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done
if [ -n "$config" ]; then
    while IFS= read -r line; do
        printf 'CONFIG:%s\\n' "$line" >> "$CCS_FAKE_CURL_LOG"
    done < "$config"
fi
[ -n "$out" ] && printf '%s' "${CCS_FAKE_CURL_BODY:-{\\"ok\\":true}}" > "$out"
printf '%s' "${CCS_FAKE_CURL_STATUS:-200}"
"""
    )
    fake_curl.chmod(0o755)


def read_pty_until(master_fd: int, text: str, timeout: float = 5) -> str:
    needle = text.encode()
    data = b""
    deadline = time.monotonic() + timeout
    while needle not in data and time.monotonic() < deadline:
        ready, _, _ = select.select([master_fd], [], [], 0.05)
        if not ready:
            continue
        try:
            chunk = os.read(master_fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        data += chunk
    output = data.decode("utf-8", "replace")
    assert text in output, output
    return output


def test_script_is_executable_and_has_valid_shell_syntax(_isolate_home):
    mode = CCS.stat().st_mode
    assert mode & stat.S_IXUSR
    subprocess.run(["sh", "-n", str(CCS)], check=True)


def test_version_matches_release_prep(_isolate_home):
    result = run(_isolate_home, "--version")

    assert result.stdout.strip() == "ccs 0.7.0"


def test_init_creates_config_layout(_isolate_home):
    result = run(_isolate_home, "init")

    assert result.returncode == 0
    assert (_isolate_home / ".config/ccs/providers").is_dir()
    assert (_isolate_home / ".config/ccs/active").exists()


def test_set_and_use_api_key_provider(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "kimi", "--base-url", "https://kimi.example", "--key", "sk-FAKE")
    result = run(_isolate_home, "use", "kimi", "--no-verify")

    conf = provider_conf(_isolate_home, "kimi")
    data = settings(_isolate_home)
    assert "switched -> kimi" in result.stdout
    assert "Same terminal cleanup" not in result.stdout
    assert conf["auth"] == "api_key"
    assert conf["key"] == "sk-FAKE"
    assert data["env"]["ANTHROPIC_BASE_URL"] == "https://kimi.example"
    assert data["env"]["ANTHROPIC_API_KEY"] == "sk-FAKE"
    assert "ANTHROPIC_AUTH_TOKEN" not in data["env"]
    assert "apiKeyHelper" not in data


def test_auth_token_provider_writes_auth_token_only(_isolate_home):
    run(_isolate_home, "init")
    run(
        _isolate_home,
        "set",
        "openrouter",
        "--base-url",
        "https://openrouter.example/anthropic",
        "--key",
        "sk-or",
        "--use-auth-token",
    )
    run(_isolate_home, "use", "openrouter", "--no-verify")

    data = settings(_isolate_home)
    assert data["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-or"
    assert data["env"]["ANTHROPIC_BASE_URL"] == "https://openrouter.example/anthropic"
    assert "ANTHROPIC_API_KEY" not in data["env"]


def test_deepseek_provider_defaults_to_auth_token(_isolate_home):
    run(_isolate_home, "init")
    run(
        _isolate_home,
        "set",
        "ds",
        "--base-url",
        "https://api.deepseek.com/anthropic",
        "--key",
        "sk-ds",
    )
    run(_isolate_home, "use", "ds", "--no-verify")

    conf = provider_conf(_isolate_home, "ds")
    data = settings(_isolate_home)
    assert conf["auth"] == "auth_token"
    assert data["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-ds"
    assert "ANTHROPIC_API_KEY" not in data["env"]


def test_switch_between_auth_types_cleans_previous_secret(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "token", "--base-url", "https://token.example", "--key", "sk-token", "--use-auth-token")
    run(_isolate_home, "set", "api", "--base-url", "https://api.example", "--key", "sk-api")

    run(_isolate_home, "use", "token", "--no-verify")
    data = settings(_isolate_home)
    assert data["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-token"
    assert "ANTHROPIC_API_KEY" not in data["env"]

    run(_isolate_home, "use", "api", "--no-verify")
    data = settings(_isolate_home)
    raw = (_isolate_home / ".claude/settings.json").read_text()
    assert data["env"]["ANTHROPIC_API_KEY"] == "sk-api"
    assert "ANTHROPIC_AUTH_TOKEN" not in data["env"]
    assert "sk-token" not in raw


def test_use_warns_about_opposite_secret_in_current_shell(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "api", "--base-url", "https://api.example", "--key", "sk-api")

    result = run(
        _isolate_home,
        "use",
        "api",
        "--no-verify",
        env_extra={"ANTHROPIC_AUTH_TOKEN": "shell-token"},
    )

    assert "switched -> api" in result.stdout
    assert "Same terminal cleanup: unset ANTHROPIC_AUTH_TOKEN" in result.stdout
    assert "current shell exports ANTHROPIC_AUTH_TOKEN" in result.stderr
    assert "shell-token" not in result.stderr


def test_use_warns_when_deepseek_provider_uses_api_key(_isolate_home):
    run(_isolate_home, "init")
    run(
        _isolate_home,
        "set",
        "ds",
        "--base-url",
        "https://api.deepseek.com/anthropic",
        "--key",
        "sk-ds",
        "--use-api-key",
    )

    result = run(_isolate_home, "use", "ds", "--no-verify")

    assert "switched -> ds" in result.stdout
    assert "DeepSeek Claude Code docs use ANTHROPIC_AUTH_TOKEN" in result.stdout
    assert "ccs set ds --use-auth-token && ccs use ds" in result.stdout


def test_use_shell_mode_prints_eval_safe_cleanup(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "api", "--base-url", "https://api.example", "--key", "sk-api")

    result = run(
        _isolate_home,
        "use",
        "api",
        "--no-verify",
        "--shell",
        env_extra={"ANTHROPIC_AUTH_TOKEN": "shell-token"},
    )

    data = settings(_isolate_home)
    assert data["env"]["ANTHROPIC_API_KEY"] == "sk-api"
    assert "switched -> api" not in result.stdout
    assert "base_url:" not in result.stdout
    assert "unset ANTHROPIC_API_KEY" in result.stdout
    assert "unset ANTHROPIC_AUTH_TOKEN" in result.stdout
    assert "unset ANTHROPIC_BASE_URL" in result.stdout
    assert "switched -> api" in result.stderr
    assert "Current shell cleanup commands were printed to stdout." in result.stderr
    assert "current shell exports ANTHROPIC_AUTH_TOKEN" not in result.stderr
    assert "shell-token" not in result.stdout
    assert "shell-token" not in result.stderr


def test_use_shell_mode_keeps_verify_failure_off_stdout(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "bad", "--base-url", "file:///nope", "--key", "sk-X")

    result = run(_isolate_home, "use", "bad", "--shell", check=False)

    assert result.returncode != 0
    assert "verify failed" not in result.stdout
    assert "Use --no-verify" not in result.stdout
    assert "verify failed" in result.stderr
    assert "Use --no-verify" in result.stderr


def test_settings_json_preserves_unrelated_fields_and_env(_isolate_home):
    settings_file = _isolate_home / ".claude/settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(
        json.dumps(
            {
                "theme": "dark",
                "apiKeyHelper": "/tmp/old-helper",
                "permissions": {"allow": ["Bash(*)"]},
                "env": {"CUSTOM_VAR": "x", "ANTHROPIC_API_KEY": "old"},
            }
        )
    )

    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://k.example", "--key", "sk-X")
    run(_isolate_home, "use", "k", "--no-verify")

    data = settings(_isolate_home)
    raw = settings_file.read_text()
    assert data["theme"] == "dark"
    assert data["permissions"] == {"allow": ["Bash(*)"]}
    assert data["env"]["CUSTOM_VAR"] == "x"
    assert data["env"]["ANTHROPIC_BASE_URL"] == "https://k.example"
    assert data["env"]["ANTHROPIC_API_KEY"] == "sk-X"
    assert "apiKeyHelper" not in data
    assert "old" not in raw


def test_settings_json_preserves_unrelated_env_json_escapes(_isolate_home):
    settings_file = _isolate_home / ".claude/settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(
        '{"env":{"CUSTOM_UNICODE":"x\\u0026y","CUSTOM_NEWLINE":"a\\nb","CUSTOM_TAB":"a\\tb","ANTHROPIC_API_KEY":"old"}}'
    )

    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://k.example", "--key", "sk-X")
    run(_isolate_home, "use", "k", "--no-verify")

    data = json.loads(settings_file.read_text())
    assert data["env"]["CUSTOM_UNICODE"] == "x&y"
    assert data["env"]["CUSTOM_NEWLINE"] == "a\nb"
    assert data["env"]["CUSTOM_TAB"] == "a\tb"
    assert data["env"]["ANTHROPIC_API_KEY"] == "sk-X"


def test_use_escapes_control_chars_in_env_value(_isolate_home):
    run(_isolate_home, "init")
    value = "a\x08b\x0cc"
    run(
        _isolate_home,
        "set",
        "k",
        "--base-url",
        "https://k.example",
        "--key",
        "sk-X",
        "-e",
        f"ANTHROPIC_DEFAULT_OPUS_MODEL_DESCRIPTION={value}",
    )
    run(_isolate_home, "use", "k", "--no-verify")

    raw = (_isolate_home / ".claude/settings.json").read_text()
    data = json.loads(raw)
    assert data["env"]["ANTHROPIC_DEFAULT_OPUS_MODEL_DESCRIPTION"] == value
    assert "\x08" not in raw
    assert "\x0c" not in raw


def test_use_preserves_non_string_env_values(_isolate_home):
    settings_file = _isolate_home / ".claude/settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(
        json.dumps(
            {
                "env": {
                    "CLAUDE_CODE_MAX_OUTPUT_TOKENS": 8192,
                    "SOME_FLAG": True,
                    "ANTHROPIC_API_KEY": "old",
                }
            }
        )
    )

    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://k.example", "--key", "sk-X")
    run(_isolate_home, "use", "k", "--no-verify")

    data = settings(_isolate_home)
    assert data["env"]["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == 8192
    assert data["env"]["SOME_FLAG"] is True
    assert data["env"]["ANTHROPIC_API_KEY"] == "sk-X"


def test_use_preserves_multiline_object_env_values(_isolate_home):
    settings_file = _isolate_home / ".claude/settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(
        """{
  "env": {
    "CUSTOM_OBJECT": {
      "limit": 8192,
      "enabled": true,
      "label": "héllo-世界"
    },
    "CUSTOM_ARRAY": [
      "alpha",
      "beta"
    ],
    "ANTHROPIC_API_KEY": "old"
  }
}
"""
    )

    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://k.example", "--key", "sk-X")
    run(_isolate_home, "use", "k", "--no-verify")

    data = settings(_isolate_home)
    assert data["env"]["CUSTOM_OBJECT"] == {"limit": 8192, "enabled": True, "label": "héllo-世界"}
    assert data["env"]["CUSTOM_ARRAY"] == ["alpha", "beta"]
    assert data["env"]["ANTHROPIC_API_KEY"] == "sk-X"


def test_use_preserves_nested_other_fields(_isolate_home):
    settings_file = _isolate_home / ".claude/settings.json"
    settings_file.parent.mkdir(parents=True)
    original = {
        "permissions": {"allow": ["Bash(*)"], "deny": [{"tool": "Read", "path": "héllo-世界"}]},
        "hooks": {"PostToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": "echo héllo-世界"}]}]},
        "env": {"CUSTOM_VAR": "x", "ANTHROPIC_API_KEY": "old"},
    }
    settings_file.write_text(json.dumps(original, ensure_ascii=False, indent=2))

    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://k.example", "--key", "sk-X")
    run(_isolate_home, "use", "k", "--no-verify")

    data = settings(_isolate_home)
    assert data["permissions"] == original["permissions"]
    assert data["hooks"] == original["hooks"]
    assert data["env"]["CUSTOM_VAR"] == "x"
    assert data["env"]["ANTHROPIC_API_KEY"] == "sk-X"


def test_set_updates_active_provider_and_reapplies_settings(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://old.example", "--key", "sk-old")
    run(_isolate_home, "use", "k", "--no-verify")

    result = run(
        _isolate_home,
        "set",
        "k",
        "--base-url",
        "https://new.example",
        "--key",
        "sk-new",
        "--use-auth-token",
        "--model",
        "claude-sonnet-4-6",
        "--opus-model",
        "claude-opus-4-7",
        "--sonnet-model",
        "claude-sonnet-4-6",
        "--haiku-model",
        "claude-haiku-4-5",
        "-e",
        "ANTHROPIC_DEFAULT_OPUS_MODEL_DESCRIPTION=Opus through provider",
        "-e",
        "ANTHROPIC_CUSTOM_MODEL_OPTION=provider-custom-model",
        "-e",
        "CLAUDE_CODE_SUBAGENT_MODEL=provider-subagent-model",
    )

    conf = provider_conf(_isolate_home, "k")
    data = settings(_isolate_home)
    assert "active reapplied" in result.stdout
    assert conf["auth"] == "auth_token"
    assert conf["ANTHROPIC_MODEL"] == "claude-sonnet-4-6"
    assert conf["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "claude-opus-4-7"
    assert conf["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "claude-sonnet-4-6"
    assert conf["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "claude-haiku-4-5"
    assert conf["ANTHROPIC_DEFAULT_OPUS_MODEL_DESCRIPTION"] == "Opus through provider"
    assert conf["ANTHROPIC_CUSTOM_MODEL_OPTION"] == "provider-custom-model"
    assert conf["CLAUDE_CODE_SUBAGENT_MODEL"] == "provider-subagent-model"
    assert data["env"]["ANTHROPIC_BASE_URL"] == "https://new.example"
    assert data["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-new"
    assert data["env"]["ANTHROPIC_MODEL"] == "claude-sonnet-4-6"
    assert data["env"]["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "claude-opus-4-7"
    assert data["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "claude-sonnet-4-6"
    assert data["env"]["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "claude-haiku-4-5"
    assert data["env"]["ANTHROPIC_DEFAULT_OPUS_MODEL_DESCRIPTION"] == "Opus through provider"
    assert data["env"]["ANTHROPIC_CUSTOM_MODEL_OPTION"] == "provider-custom-model"
    assert data["env"]["CLAUDE_CODE_SUBAGENT_MODEL"] == "provider-subagent-model"
    assert "ANTHROPIC_API_KEY" not in data["env"]


def test_unset_model_and_extra_env(_isolate_home):
    run(_isolate_home, "init")
    run(
        _isolate_home,
        "set",
        "k",
        "--base-url",
        "https://k.example",
        "--key",
        "sk-X",
        "--model",
        "model-a",
        "-e",
        "ANTHROPIC_DEFAULT_OPUS_MODEL=model-opus",
        "-e",
        "CLAUDE_CODE_SUBAGENT_MODEL=subagent-model",
    )
    run(_isolate_home, "use", "k", "--no-verify")

    run(
        _isolate_home,
        "set",
        "k",
        "--unset-model",
        "--unset-env",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "--unset-env",
        "CLAUDE_CODE_SUBAGENT_MODEL",
    )

    conf = provider_conf(_isolate_home, "k")
    data = settings(_isolate_home)
    assert "ANTHROPIC_MODEL" not in conf
    assert "ANTHROPIC_DEFAULT_OPUS_MODEL" not in conf
    assert "CLAUDE_CODE_SUBAGENT_MODEL" not in conf
    assert "ANTHROPIC_MODEL" not in data["env"]
    assert "ANTHROPIC_DEFAULT_OPUS_MODEL" not in data["env"]
    assert "CLAUDE_CODE_SUBAGENT_MODEL" not in data["env"]


def test_rm_active_provider_clears_managed_env(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://k.example", "--key", "sk-X")
    run(_isolate_home, "use", "k", "--no-verify")
    run(_isolate_home, "rm", "k")

    data = settings(_isolate_home)
    assert (_isolate_home / ".config/ccs/active").read_text() == ""
    assert not (_isolate_home / ".config/ccs/providers/k.conf").exists()
    assert "ANTHROPIC_BASE_URL" not in data["env"]
    assert "ANTHROPIC_API_KEY" not in data["env"]


def test_show_masks_key_and_stdin_key_is_supported(_isolate_home):
    run(_isolate_home, "init")
    run(
        _isolate_home,
        "set",
        "k",
        "--base-url",
        "https://k.example",
        "--key",
        "-",
        input_text="sk-secret\n",
    )

    masked = run(_isolate_home, "show", "k").stdout
    raw = run(_isolate_home, "show", "k", "--show-key").stdout
    assert "<len=9>" in masked
    assert "sk-secret" not in masked
    assert "sk-secret" in raw


def test_current_and_ls_show_active_provider(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://k.example", "--key", "sk-X")
    run(_isolate_home, "use", "k", "--no-verify")

    current = run(_isolate_home, "current").stdout
    listing = run(_isolate_home, "ls").stdout
    assert current.strip() == "k -> https://k.example"
    assert "*  k" in listing
    assert "ANTHROPIC_API_KEY" in listing


def test_ls_widens_columns_for_long_provider_names(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "x", "--base-url", "https://x.example", "--key", "sk-X")
    run(
        _isolate_home,
        "set",
        "very-long-provider-name",
        "--base-url",
        "https://much-longer-base-url.example.com/anthropic",
        "--key",
        "sk-Y",
    )

    listing = run(_isolate_home, "ls").stdout
    assert "very-long-provider-name" in listing
    assert "https://much-longer-base-url.example.com/anthropic" in listing
    long_line = next(line for line in listing.splitlines() if "very-long-provider-name" in line)
    short_line = next(line for line in listing.splitlines() if line.endswith("<len=4>") and "very-long" not in line)
    header_line = next(line for line in listing.splitlines() if "Name" in line and "Base URL" in line)
    assert (
        long_line.index("ANTHROPIC_API_KEY") == short_line.index("ANTHROPIC_API_KEY") == header_line.index("Secret env")
    )


def test_set_help_uses_simple_auth_flags(_isolate_home):
    result = run(_isolate_home, "set", "--help")

    assert "--use-api-key" in result.stdout
    assert "--use-auth-token" in result.stdout
    assert "--opus-model" in result.stdout
    assert "--sonnet-model" in result.stdout
    assert "--haiku-model" in result.stdout
    assert "--auth " not in result.stdout
    assert "api_key|auth_token" not in result.stdout


def test_top_level_help_mentions_shell_use_mode(_isolate_home):
    result = run(_isolate_home, "--help")

    assert "ccs preset <deepseek|openrouter> --key KEY [--name NAME]" in result.stdout
    assert "ccs use <name> [--no-verify] [--shell]" in result.stdout
    assert "ccs doctor" in result.stdout


def test_version_command_prints_semver(_isolate_home):
    for flag in ("--version", "-v", "version"):
        result = run(_isolate_home, flag)
        assert result.returncode == 0
        assert result.stdout.startswith("ccs ")
        assert result.stdout.strip() != "ccs"


def test_set_rejects_conflicting_auth_flags(_isolate_home):
    result = run(_isolate_home, "set", "k", "--use-api-key", "--use-auth-token", check=False)

    assert result.returncode != 0
    assert "cannot be used together" in result.stderr


def test_interactive_non_tty_fallback_prompts_one_by_one(_isolate_home):
    result = run(
        _isolate_home,
        "set",
        input_text="k\nhttps://k.example\ny\nsk-X\nmodel-x\nopus-x\nsonnet-x\nhaiku-x\n",
    )

    conf = provider_conf(_isolate_home, "k")
    prompts = result.stderr
    assert "Provider name:" in prompts
    assert "Use ANTHROPIC_AUTH_TOKEN / Bearer auth?" in prompts
    assert "Key for ANTHROPIC_AUTH_TOKEN" in prompts
    assert conf["auth"] == "auth_token"
    assert conf["key"] == "sk-X"
    assert conf["ANTHROPIC_BASE_URL"] == "https://k.example"
    assert conf["ANTHROPIC_MODEL"] == "model-x"
    assert conf["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "opus-x"
    assert conf["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "sonnet-x"
    assert conf["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "haiku-x"


def test_interactive_model_aliases_default_to_model(_isolate_home):
    result = run(_isolate_home, "set", input_text="k\nhttps://k.example\n\nsk-X\nmodel-x\n\n\n\n")

    conf = provider_conf(_isolate_home, "k")
    assert result.returncode == 0
    assert conf["auth"] == "api_key"
    assert conf["ANTHROPIC_MODEL"] == "model-x"
    assert conf["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "model-x"
    assert conf["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "model-x"
    assert conf["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "model-x"


def test_tty_auth_selector_accepts_arrow_keys(_isolate_home):
    env = {**os.environ, "HOME": str(_isolate_home)}
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    env.pop("CCS_DIR", None)
    env.pop("CLAUDE_SETTINGS_FILE", None)
    master_fd, slave_fd = pty.openpty()
    proc = None
    try:
        proc = subprocess.Popen(
            [str(CCS), "set", "arrow"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            close_fds=True,
        )
        os.close(slave_fd)
        slave_fd = None

        read_pty_until(master_fd, "Base URL:")
        os.write(master_fd, b"https://arrow.example\r")
        selector = read_pty_until(master_fd, "Secret env")
        assert "\x1b[1;30;46m" in selector
        os.write(master_fd, b"\x1b[C\r")
        key_prompt = read_pty_until(master_fd, "Key for ANTHROPIC_AUTH_TOKEN")
        assert "\r\nKey for ANTHROPIC_AUTH_TOKEN" in key_prompt
        os.write(master_fd, b"sk-arrow\r")
        read_pty_until(master_fd, "Model (optional)")
        os.write(master_fd, b"\r")
        read_pty_until(master_fd, "Opus model (optional)")
        os.write(master_fd, b"\r")
        read_pty_until(master_fd, "Sonnet model (optional)")
        os.write(master_fd, b"\r")
        read_pty_until(master_fd, "Haiku model (optional)")
        os.write(master_fd, b"\r")
        read_pty_until(master_fd, "created arrow")

        assert proc.wait(timeout=5) == 0
    finally:
        if slave_fd is not None:
            os.close(slave_fd)
        os.close(master_fd)
        if proc is not None and proc.poll() is None:
            proc.terminate()

    conf = provider_conf(_isolate_home, "arrow")
    assert conf["auth"] == "auth_token"
    assert conf["key"] == "sk-arrow"


def test_verify_rejects_bad_scheme(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "bad", "--base-url", "file:///etc/passwd", "--key", "sk-X")

    result = run(_isolate_home, "verify", "bad", check=False)

    assert result.returncode != 0
    assert "unsupported scheme" in result.stdout


def test_verify_uses_auth_specific_curl_header(_isolate_home, tmp_path):
    fake_bin = tmp_path / "bin"
    log_file = tmp_path / "curl.log"
    write_fake_curl(fake_bin, log_file)
    env_extra = {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "CCS_FAKE_CURL_LOG": str(log_file),
    }

    run(_isolate_home, "init", env_extra=env_extra)
    run(
        _isolate_home,
        "set",
        "api",
        "--base-url",
        "https://api.example",
        "--key",
        'sk-"api\\key',
        "--opus-model",
        "model-opus",
        env_extra=env_extra,
    )
    run(_isolate_home, "verify", "api", env_extra=env_extra)
    api_args = log_file.read_text()
    assert 'sk-"api\\key' not in "\n".join(line for line in api_args.splitlines() if line.startswith("ARG:"))
    assert 'CONFIG:header = "x-api-key: sk-\\"api\\\\key"' in api_args
    assert 'CONFIG:header = "Authorization: Bearer' not in api_args
    assert '"model":"model-opus"' in api_args

    log_file.write_text("")
    run(
        _isolate_home,
        "set",
        "token",
        "--base-url",
        "https://token.example",
        "--key",
        "sk-token",
        "--use-auth-token",
        env_extra=env_extra,
    )
    run(_isolate_home, "verify", "token", env_extra=env_extra)
    token_args = log_file.read_text()
    assert "sk-token" not in "\n".join(line for line in token_args.splitlines() if line.startswith("ARG:"))
    assert 'CONFIG:header = "Authorization: Bearer sk-token"' in token_args
    assert 'CONFIG:header = "x-api-key:' not in token_args


@pytest.mark.parametrize(
    ("status", "body", "expected_returncode", "expected_text"),
    [
        ("200", '{"ok":true}', 0, "OK (200)"),
        ("401", '{"error":{"message":"bad key"}}', 1, "Authentication failed (401)"),
        ("403", '{"error":{"message":"denied"}}', 1, "Access denied (403)"),
        ("400", '{"error":{"type":"invalid_api_key","message":"bad key"}}', 1, "Provider rejected: bad key"),
        ("400", '{"error":{"type":"overloaded_error","message":"try later"}}', 0, "Reachable (HTTP 400)"),
        ("500", '{"error":{"message":"server"}}', 1, "Server error (HTTP 500)"),
        ("000", "", 1, "unexpected HTTP status 000"),
    ],
)
def test_verify_status_branches(_isolate_home, tmp_path, status, body, expected_returncode, expected_text):
    fake_bin = tmp_path / "bin"
    log_file = tmp_path / "curl.log"
    write_fake_curl(fake_bin, log_file)
    env_extra = {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "CCS_FAKE_CURL_LOG": str(log_file),
        "CCS_FAKE_CURL_STATUS": status,
        "CCS_FAKE_CURL_BODY": body,
    }

    run(_isolate_home, "init", env_extra=env_extra)
    run(_isolate_home, "set", "api", "--base-url", "https://api.example", "--key", "sk-api", env_extra=env_extra)
    result = run(_isolate_home, "verify", "api", check=False, env_extra=env_extra)

    assert result.returncode == expected_returncode
    assert expected_text in result.stdout


def test_verify_warns_on_plain_http(_isolate_home, tmp_path):
    fake_bin = tmp_path / "bin"
    log_file = tmp_path / "curl.log"
    write_fake_curl(fake_bin, log_file)
    env_extra = {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "CCS_FAKE_CURL_LOG": str(log_file),
    }

    run(_isolate_home, "init", env_extra=env_extra)
    run(_isolate_home, "set", "api", "--base-url", "http://api.example", "--key", "sk-api", env_extra=env_extra)
    result = run(_isolate_home, "verify", "api", env_extra=env_extra)

    assert "verifying against http://api.example/v1/messages" in result.stderr
    assert "warning: sending provider secret over plain HTTP" in result.stderr


def test_verify_warns_on_non_loopback_127_like_hostname(_isolate_home, tmp_path):
    fake_bin = tmp_path / "bin"
    log_file = tmp_path / "curl.log"
    write_fake_curl(fake_bin, log_file)
    env_extra = {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "CCS_FAKE_CURL_LOG": str(log_file),
    }

    run(_isolate_home, "init", env_extra=env_extra)
    run(_isolate_home, "set", "api", "--base-url", "http://127.evil.example", "--key", "sk-api", env_extra=env_extra)
    result = run(_isolate_home, "verify", "api", env_extra=env_extra)

    assert "verifying against http://127.evil.example/v1/messages" in result.stderr
    assert "warning: sending provider secret over plain HTTP" in result.stderr


@pytest.mark.parametrize(
    "base_url",
    [
        "http://127.0.0.1",
        "http://localhost",
        "http://[::1]",
    ],
)
def test_verify_silent_on_loopback_http(_isolate_home, tmp_path, base_url):
    fake_bin = tmp_path / "bin"
    log_file = tmp_path / "curl.log"
    write_fake_curl(fake_bin, log_file)
    env_extra = {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "CCS_FAKE_CURL_LOG": str(log_file),
    }

    run(_isolate_home, "init", env_extra=env_extra)
    run(_isolate_home, "set", "api", "--base-url", base_url, "--key", "sk-api", env_extra=env_extra)
    result = run(_isolate_home, "verify", "api", env_extra=env_extra)

    assert f"verifying against {base_url}/v1/messages" in result.stderr
    assert "warning: sending provider secret over plain HTTP" not in result.stderr


def test_set_rejects_invalid_provider_name(_isolate_home):
    result = run(_isolate_home, "set", "../etc", "--base-url", "https://x", "--key", "k", check=False)
    assert result.returncode != 0
    assert "provider name may only contain" in result.stderr


def test_preset_deepseek_configures_provider(_isolate_home):
    run(_isolate_home, "init")

    result = run(_isolate_home, "preset", "deepseek", "--key", "sk-ds")
    run(_isolate_home, "use", "deepseek", "--no-verify")

    conf = provider_conf(_isolate_home, "deepseek")
    data = settings(_isolate_home)
    assert "created deepseek" in result.stdout
    assert conf["auth"] == "auth_token"
    assert conf["ANTHROPIC_BASE_URL"] == "https://api.deepseek.com/anthropic"
    assert conf["ANTHROPIC_MODEL"] == "deepseek-v4-pro[1m]"
    assert conf["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "deepseek-v4-pro[1m]"
    assert conf["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "deepseek-v4-pro[1m]"
    assert conf["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "deepseek-v4-flash"
    assert conf["CLAUDE_CODE_SUBAGENT_MODEL"] == "deepseek-v4-flash"
    assert conf["CLAUDE_CODE_EFFORT_LEVEL"] == "max"
    assert data["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-ds"
    assert data["env"]["CLAUDE_CODE_SUBAGENT_MODEL"] == "deepseek-v4-flash"
    assert data["env"]["CLAUDE_CODE_EFFORT_LEVEL"] == "max"
    assert "ANTHROPIC_API_KEY" not in data["env"]


def test_preset_openrouter_supports_custom_name_and_stdin_key(_isolate_home):
    run(_isolate_home, "init")

    result = run(_isolate_home, "preset", "openrouter", "--name", "or", "--key", "-", input_text="sk-or\n")
    run(_isolate_home, "use", "or", "--no-verify")

    conf = provider_conf(_isolate_home, "or")
    data = settings(_isolate_home)
    assert "created or" in result.stdout
    assert conf["auth"] == "auth_token"
    assert conf["key"] == "sk-or"
    assert conf["ANTHROPIC_BASE_URL"] == "https://openrouter.ai/api"
    assert conf["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "~anthropic/claude-opus-latest"
    assert conf["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "~anthropic/claude-sonnet-latest"
    assert conf["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "~anthropic/claude-haiku-latest"
    assert conf["CLAUDE_CODE_SUBAGENT_MODEL"] == "~anthropic/claude-opus-latest"
    assert data["env"]["CLAUDE_CODE_SUBAGENT_MODEL"] == "~anthropic/claude-opus-latest"


def test_preset_rejects_unknown_provider(_isolate_home):
    result = run(_isolate_home, "preset", "unknown", "--key", "sk-x", check=False)

    assert result.returncode != 0
    assert "unknown preset: unknown" in result.stderr


def test_doctor_reports_active_provider_without_failures(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://k.example", "--key", "sk-k")
    run(_isolate_home, "use", "k", "--no-verify")

    result = run(_isolate_home, "doctor")

    assert result.returncode == 0
    assert "ccs doctor" in result.stdout
    assert "ok:   active provider: k" in result.stdout
    assert "ok:   active provider base URL: https://k.example" in result.stdout
    assert "summary: 0 failure(s)" in result.stdout


def test_doctor_fails_when_active_provider_file_is_missing(_isolate_home):
    run(_isolate_home, "init")
    (_isolate_home / ".config/ccs/active").write_text("ghost\n")

    result = run(_isolate_home, "doctor", check=False)

    assert result.returncode == 1
    assert "fail: active provider file is missing" in result.stdout
    assert "summary: 1 failure(s)" in result.stdout


def test_doctor_warns_about_current_shell_secret_conflict(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "api", "--base-url", "https://api.example", "--key", "sk-api")
    run(_isolate_home, "use", "api", "--no-verify")

    result = run(_isolate_home, "doctor", env_extra={"ANTHROPIC_AUTH_TOKEN": "shell-token"})

    assert result.returncode == 0
    assert "current shell exports ANTHROPIC_AUTH_TOKEN but active provider uses ANTHROPIC_API_KEY" in result.stdout
    assert "shell-token" not in result.stdout


def test_doctor_warns_when_deepseek_provider_uses_api_key(_isolate_home):
    run(_isolate_home, "init")
    run(
        _isolate_home,
        "set",
        "ds",
        "--base-url",
        "https://api.deepseek.com/anthropic",
        "--key",
        "sk-ds",
        "--use-api-key",
    )
    run(_isolate_home, "use", "ds", "--no-verify")

    result = run(_isolate_home, "doctor")

    assert result.returncode == 0
    assert "DeepSeek Claude Code docs use ANTHROPIC_AUTH_TOKEN" in result.stdout
    assert "ccs set ds --use-auth-token && ccs use ds" in result.stdout


def test_rm_non_active_provider_does_not_touch_settings(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "a", "--base-url", "https://a", "--key", "sk-a")
    run(_isolate_home, "set", "b", "--base-url", "https://b", "--key", "sk-b")
    run(_isolate_home, "use", "a", "--no-verify")

    result = run(_isolate_home, "rm", "b")
    assert "removed b" in result.stdout

    data = settings(_isolate_home)
    assert data["env"]["ANTHROPIC_BASE_URL"] == "https://a"
    assert data["env"]["ANTHROPIC_API_KEY"] == "sk-a"


def test_model_with_special_chars_encoded_correctly(_isolate_home):
    run(_isolate_home, "init")
    run(
        _isolate_home,
        "set",
        "k",
        "--base-url",
        "https://k",
        "--key",
        "sk-k",
        "--model",
        'model"with\\quotes',
    )
    conf = provider_conf(_isolate_home, "k")
    assert conf["ANTHROPIC_MODEL"] == 'model"with\\quotes'
    raw = (_isolate_home / ".config/ccs/providers/k.conf").read_text()
    assert 'ANTHROPIC_MODEL=model"with\\quotes' in raw


def test_provider_file_orders_env_keys_like_provider_env_keys(_isolate_home):
    keys = provider_env_keys()
    args = ["set", "ordered", "--base-url", "https://ordered.example", "--key", "sk-ordered"]
    for key in keys:
        if key == "ANTHROPIC_BASE_URL":
            continue
        args.extend(["-e", f"{key}=value-for-{key}"])

    run(_isolate_home, "init")
    run(_isolate_home, *args)

    lines = (_isolate_home / ".config/ccs/providers/ordered.conf").read_text().splitlines()
    env_keys = [line.split("=", 1)[0] for line in lines[2:]]
    assert env_keys == keys


def test_provider_file_has_strict_perms(_isolate_home):
    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://k.example", "--key", "sk-X")

    mode = (_isolate_home / ".config/ccs/providers/k.conf").stat().st_mode
    assert mode & 0o077 == 0


def test_use_with_corrupt_settings_json(_isolate_home):
    settings_file = _isolate_home / ".claude/settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text("this is not json")

    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://k", "--key", "sk-k")
    result = run(_isolate_home, "use", "k", "--no-verify")

    assert result.returncode == 0
    assert "switched -> k" in result.stdout
    data = settings(_isolate_home)
    assert data["env"]["ANTHROPIC_BASE_URL"] == "https://k"
    assert data["env"]["ANTHROPIC_API_KEY"] == "sk-k"


def test_use_fails_when_settings_path_is_not_file_and_keeps_active(_isolate_home):
    settings_file = _isolate_home / ".claude/settings.json"
    run(_isolate_home, "init")
    run(_isolate_home, "set", "old", "--base-url", "https://old", "--key", "sk-old")
    run(_isolate_home, "use", "old", "--no-verify")
    run(_isolate_home, "set", "new", "--base-url", "https://new", "--key", "sk-new")

    settings_file.unlink()
    settings_file.mkdir()
    result = run(_isolate_home, "use", "new", "--no-verify", check=False)

    assert result.returncode != 0
    assert "settings path exists but is not a regular file" in result.stderr
    assert "switched -> new" not in result.stdout
    assert (_isolate_home / ".config/ccs/active").read_text().strip() == "old"


def test_rm_active_fails_when_settings_path_is_not_file_and_keeps_state(_isolate_home):
    settings_file = _isolate_home / ".claude/settings.json"
    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://k", "--key", "sk-k")
    run(_isolate_home, "use", "k", "--no-verify")

    settings_file.unlink()
    settings_file.mkdir()
    result = run(_isolate_home, "rm", "k", check=False)

    assert result.returncode != 0
    assert "settings path exists but is not a regular file" in result.stderr
    assert "removed k" not in result.stdout
    assert (_isolate_home / ".config/ccs/active").read_text().strip() == "k"
    assert (_isolate_home / ".config/ccs/providers/k.conf").exists()


def test_install_sh_fails_on_sha256_mismatch(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_curl = fake_bin / "curl"
    fake_curl.write_text(
        """#!/bin/sh
out=
while [ "$#" -gt 0 ]; do
    if [ "$1" = "-o" ]; then
        out=$2
        shift 2
        continue
    fi
    shift
done
[ -n "$out" ] && printf 'not the real ccs' > "$out"
"""
    )
    fake_curl.chmod(0o755)
    install_dir = tmp_path / "install"

    result = subprocess.run(
        ["sh", str(INSTALL)],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "CCS_INSTALL_DIR": str(install_dir),
            "CCS_INSTALL_SHA256": "0000000000000000000000000000000000000000000000000000000000000000",
        },
        check=False,
    )

    assert result.returncode != 0
    assert "checksum mismatch" in result.stderr
    assert not (install_dir / "ccs").exists()


@pytest.mark.parametrize(
    ("flag", "payload"),
    [
        ("--base-url", "https://ok\nANTHROPIC_DEFAULT_HAIKU_MODEL=evil"),
        ("--key", "sk\nANTHROPIC_MODEL=evil"),
    ],
)
def test_set_rejects_newline_in_core_values(_isolate_home, flag, payload):
    run(_isolate_home, "init")
    args = ["set", "p", "--base-url", "https://ok", "--key", "sk"]
    # Replace whichever field is under test with the malicious payload.
    if flag == "--base-url":
        args[3] = payload
    else:
        args[5] = payload
    result = run(_isolate_home, *args, check=False)

    assert result.returncode != 0
    assert "may not contain newline" in result.stderr
    assert not (_isolate_home / ".config/ccs/providers/p.conf").exists()


@pytest.mark.parametrize("ctrl", ["a\nb", "a\tb", "a\rb"])
def test_set_rejects_control_chars_in_env_value(_isolate_home, ctrl):
    run(_isolate_home, "init")
    result = run(
        _isolate_home,
        "set",
        "p",
        "--base-url",
        "https://ok",
        "--key",
        "sk",
        "-e",
        f"ANTHROPIC_MODEL={ctrl}",
        check=False,
    )

    assert result.returncode != 0
    assert "may not contain newline, tab, or carriage return" in result.stderr


def test_empty_home_without_overrides_refuses(_isolate_home):
    result = run(_isolate_home, "ls", check=False, env_extra={"HOME": ""})

    assert result.returncode != 0
    assert "HOME is empty" in result.stderr


def test_empty_home_with_overrides_works(_isolate_home, tmp_path):
    cfg = tmp_path / "cfg"
    settings_file = tmp_path / "settings.json"
    result = run(
        _isolate_home,
        "init",
        env_extra={
            "HOME": "",
            "CCS_DIR": str(cfg),
            "CLAUDE_SETTINGS_FILE": str(settings_file),
        },
    )

    assert result.returncode == 0
    assert cfg.is_dir()


def test_isolation_ignores_inherited_ccs_dir_override(_isolate_home, tmp_path, monkeypatch):
    # A CCS_DIR/CLAUDE_SETTINGS_FILE exported in the surrounding shell must not
    # redirect writes away from the isolated HOME. The autouse _isolate_home
    # fixture delenv's them and run() strips them again; simulate an inherited
    # export via os.environ (not env_extra) to pin that both layers hold.
    stray = tmp_path / "stray-config"
    stray_settings = tmp_path / "stray-settings.json"
    monkeypatch.setenv("CCS_DIR", str(stray))
    monkeypatch.setenv("CLAUDE_SETTINGS_FILE", str(stray_settings))

    run(_isolate_home, "init")
    run(_isolate_home, "set", "k", "--base-url", "https://k.example", "--key", "sk-X")
    run(_isolate_home, "use", "k", "--no-verify")

    assert (_isolate_home / ".config/ccs").is_dir()
    assert (_isolate_home / ".claude/settings.json").is_file()
    assert not stray.exists()
    assert not stray_settings.exists()


def _jq_free_path(tmp_path: Path) -> str:
    """Build a PATH with the usual tools but no jq, to exercise the awk writer."""
    bin_dir = tmp_path / "nojq-bin"
    bin_dir.mkdir(exist_ok=True)
    tools = [
        "sh",
        "awk",
        "sed",
        "grep",
        "mktemp",
        "mv",
        "rm",
        "cat",
        "chmod",
        "mkdir",
        "dirname",
        "basename",
        "wc",
        "tr",
        "cut",
        "expr",
        "env",
        "printf",
        "test",
        "[",
    ]
    import shutil

    for tool in tools:
        src = shutil.which(tool)
        if src:
            (bin_dir / tool).symlink_to(src)
    return str(bin_dir)


def test_awk_fallback_preserves_fields_without_jq(_isolate_home, tmp_path):
    if not _shutil_which("jq"):
        pytest.skip("jq not installed; jq path and fallback are identical here")
    settings_file = _isolate_home / ".claude/settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text('{"permissions":{"allow":["Bash(*)"]},"env":{"CUSTOM":"x","ANTHROPIC_API_KEY":"old"}}')

    nojq = _jq_free_path(tmp_path)
    run(_isolate_home, "init", env_extra={"PATH": nojq})
    run(_isolate_home, "set", "k", "--base-url", "https://k.example", "--key", "sk-X", env_extra={"PATH": nojq})
    run(_isolate_home, "use", "k", "--no-verify", env_extra={"PATH": nojq})

    data = settings(_isolate_home)
    assert data["permissions"] == {"allow": ["Bash(*)"]}
    assert data["env"]["CUSTOM"] == "x"
    assert data["env"]["ANTHROPIC_BASE_URL"] == "https://k.example"
    assert data["env"]["ANTHROPIC_API_KEY"] == "sk-X"


def _shutil_which(name: str):
    import shutil

    return shutil.which(name)
