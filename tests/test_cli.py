"""End-to-end tests for the Python ccs-py CLI."""

from __future__ import annotations

import json
import os
import pty
import select
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY_CCS = (sys.executable, "-m", "ccs.cli")


def run(
    home: Path,
    *args: str,
    input_text: str | None = None,
    check: bool = True,
    env_extra: dict[str, str] | None = None,
):
    env = {
        **os.environ,
        "HOME": str(home),
        "CCS_VERIFY_TIMEOUT": "1",
        "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
    }
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        [*PY_CCS, *args],
        input=input_text,
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        check=False,
    )
    if check and result.returncode != 0:
        command = " ".join((*PY_CCS, *args))
        raise AssertionError(f"{command} failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
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


class HeaderCaptureServer:
    def __init__(self):
        self.headers: list[dict[str, str]] = []

        capture = self.headers

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                capture.append({key.lower(): value for key, value in self.headers.items()})
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok":true}')

            def log_message(self, _format: str, *_args) -> None:
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()


def test_python_package_exposes_only_ccs_py_script():
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'ccs-py = "ccs.cli:main"' in pyproject
    assert 'ccs = "ccs.cli:main"' not in pyproject


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
    assert "k" in listing
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
    prompts = result.stdout + result.stderr
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
            [*PY_CCS, "set", "arrow"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            cwd=ROOT,
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


def test_verify_uses_auth_specific_header(_isolate_home):
    with HeaderCaptureServer() as server:
        run(_isolate_home, "init")
        run(_isolate_home, "set", "api", "--base-url", server.base_url, "--key", "sk-api")
        run(_isolate_home, "verify", "api")
        assert server.headers[-1].get("x-api-key") == "sk-api"
        assert "authorization" not in server.headers[-1]

        run(
            _isolate_home,
            "set",
            "token",
            "--base-url",
            server.base_url,
            "--key",
            "sk-token",
            "--use-auth-token",
        )
        run(_isolate_home, "verify", "token")
        assert server.headers[-1].get("authorization") == "Bearer sk-token"
        assert "x-api-key" not in server.headers[-1]
