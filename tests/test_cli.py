"""End-to-end tests for the shell-based ccs CLI."""

import json
import os
import pty
import select
import stat
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CCS = ROOT / "bin" / "ccs"


def run(
    home: Path, *args: str, input_text: str | None = None, check: bool = True, env_extra: dict[str, str] | None = None
):
    env = {**os.environ, "HOME": str(home), "CCS_VERIFY_TIMEOUT": "1"}
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
    )

    conf = provider_conf(_isolate_home, "k")
    data = settings(_isolate_home)
    assert "active reapplied" in result.stdout
    assert conf["auth"] == "auth_token"
    assert conf["ANTHROPIC_MODEL"] == "claude-sonnet-4-6"
    assert data["env"]["ANTHROPIC_BASE_URL"] == "https://new.example"
    assert data["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-new"
    assert data["env"]["ANTHROPIC_MODEL"] == "claude-sonnet-4-6"
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
    )
    run(_isolate_home, "use", "k", "--no-verify")

    run(_isolate_home, "set", "k", "--unset-model", "--unset-env", "ANTHROPIC_DEFAULT_OPUS_MODEL")

    conf = provider_conf(_isolate_home, "k")
    data = settings(_isolate_home)
    assert "ANTHROPIC_MODEL" not in conf
    assert "ANTHROPIC_DEFAULT_OPUS_MODEL" not in conf
    assert "ANTHROPIC_MODEL" not in data["env"]
    assert "ANTHROPIC_DEFAULT_OPUS_MODEL" not in data["env"]


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


def test_set_help_uses_simple_auth_flags(_isolate_home):
    result = run(_isolate_home, "set", "--help")

    assert "--use-api-key" in result.stdout
    assert "--use-auth-token" in result.stdout
    assert "--auth " not in result.stdout
    assert "api_key|auth_token" not in result.stdout


def test_set_rejects_conflicting_auth_flags(_isolate_home):
    result = run(_isolate_home, "set", "k", "--use-api-key", "--use-auth-token", check=False)

    assert result.returncode != 0
    assert "cannot be used together" in result.stderr


def test_interactive_non_tty_fallback_prompts_one_by_one(_isolate_home):
    result = run(_isolate_home, "set", input_text="k\nhttps://k.example\ny\nsk-X\nmodel-x\n")

    conf = provider_conf(_isolate_home, "k")
    prompts = result.stderr
    assert "Provider name:" in prompts
    assert "Use ANTHROPIC_AUTH_TOKEN / Bearer auth?" in prompts
    assert "Key for ANTHROPIC_AUTH_TOKEN" in prompts
    assert conf["auth"] == "auth_token"
    assert conf["key"] == "sk-X"
    assert conf["ANTHROPIC_BASE_URL"] == "https://k.example"
    assert conf["ANTHROPIC_MODEL"] == "model-x"


def test_tty_auth_selector_accepts_arrow_keys(_isolate_home):
    env = {**os.environ, "HOME": str(_isolate_home)}
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
    fake_bin.mkdir()
    log_file = tmp_path / "curl.log"
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
    printf '%s\\n' "$1" >> "$CCS_FAKE_CURL_LOG"
    shift
done
[ -n "$out" ] && printf '{"ok":true}' > "$out"
printf 200
"""
    )
    fake_curl.chmod(0o755)
    env_extra = {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "CCS_FAKE_CURL_LOG": str(log_file),
    }

    run(_isolate_home, "init", env_extra=env_extra)
    run(_isolate_home, "set", "api", "--base-url", "https://api.example", "--key", "sk-api", env_extra=env_extra)
    run(_isolate_home, "verify", "api", env_extra=env_extra)
    api_args = log_file.read_text()
    assert "x-api-key: sk-api" in api_args
    assert "Authorization: Bearer" not in api_args

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
    assert "Authorization: Bearer sk-token" in token_args
    assert "x-api-key:" not in token_args
