"""ccs-py - Python entrypoint for the ccs provider switcher.

The shell and Python implementations intentionally share the same on-disk
layout:

  ~/.config/ccs/active
  ~/.config/ccs/providers/<name>.conf
"""

from __future__ import annotations

import json
import os
import re
import sys
import termios
import tty
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import click
from rich.console import Console
from rich.table import Table

console = Console()

CCS_DIR = Path(os.environ.get("CCS_DIR", Path.home() / ".config" / "ccs"))
PROVIDERS_DIR = CCS_DIR / "providers"
ACTIVE_FILE = CCS_DIR / "active"
SETTINGS_FILE = Path(os.environ.get("CLAUDE_SETTINGS_FILE", Path.home() / ".claude" / "settings.json"))

AUTH_API_KEY = "api_key"
AUTH_TOKEN = "auth_token"
ENV_API_KEY = "ANTHROPIC_API_KEY"
ENV_AUTH_TOKEN = "ANTHROPIC_AUTH_TOKEN"

PROVIDER_ENV_KEYS = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME",
    "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME",
)
MANAGED_ENV_KEYS = (*PROVIDER_ENV_KEYS, ENV_API_KEY, ENV_AUTH_TOKEN)
FATAL_PROVIDER_ERROR_TYPES = {
    "authentication_error",
    "invalid_api_key",
    "model_not_found",
    "not_found_error",
    "permission_error",
}

VERIFY_TIMEOUT = int(os.environ.get("CCS_VERIFY_TIMEOUT", "10"))
VERIFY_PROBE_MODEL = os.environ.get("CCS_VERIFY_PROBE_MODEL", "claude-sonnet-4-6")
NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
ANSI_RESET = "\033[0m"
ANSI_SELECTED = "\033[1;30;46m"
CLEAR_LINE = "\033[K"


def die(message: str) -> None:
    raise click.ClickException(message)


def ensure_dirs() -> None:
    PROVIDERS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        CCS_DIR.chmod(0o700)
        PROVIDERS_DIR.chmod(0o700)
    except OSError:
        pass


def init_active_file() -> None:
    ensure_dirs()
    if not ACTIVE_FILE.exists():
        ACTIVE_FILE.write_text("")
    try:
        ACTIVE_FILE.chmod(0o600)
    except OSError:
        pass


def provider_file(name: str) -> Path:
    return PROVIDERS_DIR / f"{name}.conf"


def require_provider_name(name: str) -> None:
    if not name:
        die("provider name is required")
    if not NAME_RE.fullmatch(name):
        die("provider name may only contain letters, numbers, dot, underscore, and dash")


def validate_env_key(key: str) -> None:
    if key not in PROVIDER_ENV_KEYS:
        die(f"unsupported env key '{key}'")


def read_conf(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


def provider_env(conf: dict[str, str]) -> dict[str, str]:
    return {key: conf[key] for key in PROVIDER_ENV_KEYS if key in conf}


def write_provider(name: str, auth: str, key: str, env: dict[str, str]) -> None:
    ensure_dirs()
    path = provider_file(name)
    lines = [f"auth={auth}", f"key={key}"]
    lines.extend(f"{env_key}={env[env_key]}" for env_key in PROVIDER_ENV_KEYS if env.get(env_key))
    atomic_write(path, "\n".join(lines) + "\n")


def atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        os.write(fd, content.encode())
    finally:
        os.close(fd)
    os.replace(tmp, path)


def active_name() -> str:
    if not ACTIVE_FILE.exists():
        return ""
    lines = ACTIVE_FILE.read_text().splitlines()
    return lines[0].strip() if lines else ""


def set_active(name: str) -> None:
    init_active_file()
    atomic_write(ACTIVE_FILE, f"{name}\n")


def clear_active() -> None:
    init_active_file()
    atomic_write(ACTIVE_FILE, "")


def secret_env_name(auth: str) -> str:
    return ENV_AUTH_TOKEN if auth == AUTH_TOKEN else ENV_API_KEY


def masked_key(key: str) -> str:
    return "<empty>" if not key else f"<len={len(key)}>"


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        settings = json.loads(SETTINGS_FILE.read_text())
    except json.JSONDecodeError as exc:
        die(f"malformed JSON in {SETTINGS_FILE}: {exc}")
    if not isinstance(settings, dict):
        die(f"{SETTINGS_FILE} has unexpected schema")
    return settings


def save_settings(settings: dict) -> None:
    atomic_write(SETTINGS_FILE, json.dumps(settings, indent=2, ensure_ascii=False) + "\n")


def apply_provider(name: str) -> None:
    conf = read_conf(provider_file(name))
    if not conf:
        die(f"no such provider: '{name}'")
    auth = conf.get("auth") or AUTH_API_KEY
    key = conf.get("key") or ""
    if not key:
        die(f"provider '{name}' has empty key")

    settings = load_settings()
    env = settings.get("env", {})
    if not isinstance(env, dict):
        env = {}
    preserved_env = {k: v for k, v in env.items() if k not in MANAGED_ENV_KEYS}
    settings.pop("apiKeyHelper", None)
    settings["env"] = preserved_env
    settings["env"].update(provider_env(conf))
    settings["env"][secret_env_name(auth)] = key
    save_settings(settings)


def clear_provider_env() -> None:
    settings = load_settings()
    env = settings.get("env", {})
    if not isinstance(env, dict):
        env = {}
    settings.pop("apiKeyHelper", None)
    settings["env"] = {k: v for k, v in env.items() if k not in MANAGED_ENV_KEYS}
    save_settings(settings)


def prompt_required(label: str, default: str = "") -> str:
    prompt = f"{label} [{default}]: " if default else f"{label}: "
    click.echo(prompt, nl=False, err=True)
    value = sys.stdin.readline().rstrip("\r\n")
    if not value:
        value = default
    if not value:
        die(f"{label} is required")
    return value


def prompt_optional(label: str, default: str = "", hide: bool = False) -> str:
    prompt = f"{label} [{default}]: " if default else f"{label}: "
    if hide and sys.stdin.isatty():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        chars: list[str] = []
        try:
            tty.setraw(fd)
            click.echo(prompt, nl=False, err=True)
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\r", "\n", ""):
                    break
                if ch in ("\x03", "\x04"):
                    raise KeyboardInterrupt
                chars.append(ch)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            click.echo(err=True)
        value = "".join(chars)
    else:
        click.echo(prompt, nl=False, err=True)
        value = sys.stdin.readline().rstrip("\r\n")
    return value if value else default


def render_auth_selector(selected: int) -> str:
    api = f"  {ENV_API_KEY}  "
    token = f"  {ENV_AUTH_TOKEN}  "
    if selected == 0:
        api = f"{ANSI_SELECTED} {ENV_API_KEY} {ANSI_RESET}"
    else:
        token = f"{ANSI_SELECTED} {ENV_AUTH_TOKEN} {ANSI_RESET}"
    return f"Secret env (<-/->, Enter): {api}  {token}"


def prompt_auth(default_auth: str) -> str:
    selected = 1 if default_auth == AUTH_TOKEN else 0
    if sys.stdin.isatty() and sys.stderr.isatty():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            sys.stderr.write(render_auth_selector(selected))
            sys.stderr.flush()
            while True:
                key = sys.stdin.read(1)
                if key == "\x1b":
                    key += sys.stdin.read(2)
                if key in ("\r", "\n", ""):
                    sys.stderr.write("\r\n")
                    sys.stderr.flush()
                    return AUTH_TOKEN if selected else AUTH_API_KEY
                if key in ("\x03", "\x04"):
                    raise KeyboardInterrupt
                if key in ("\x1b[D", "\x1b[C"):
                    selected = 0 if selected else 1
                    sys.stderr.write(f"\r{CLEAR_LINE}{render_auth_selector(selected)}")
                    sys.stderr.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    if default_auth == AUTH_TOKEN:
        answer = click.prompt("Use ANTHROPIC_AUTH_TOKEN / Bearer auth? [Y/n]", default="", show_default=False)
        return AUTH_API_KEY if answer.lower() in {"n", "no"} else AUTH_TOKEN
    answer = click.prompt("Use ANTHROPIC_AUTH_TOKEN / Bearer auth? [y/N]", default="", show_default=False)
    return AUTH_TOKEN if answer.lower() in {"y", "yes"} else AUTH_API_KEY


def verify_request(base_url: str, key: str, model: str, auth: str = AUTH_API_KEY) -> tuple[bool, str]:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        return False, f"unsupported scheme: {parsed.scheme or base_url}"
    url = base_url.rstrip("/") + "/v1/messages"
    body = json.dumps(
        {
            "model": model,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "hi"}],
        }
    ).encode()
    headers = {
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    if auth == AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {key}"
    else:
        headers["x-api-key"] = key
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=VERIFY_TIMEOUT) as response:
            return True, f"OK ({response.status})"
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return False, "Authentication failed (401)"
        if exc.code == 403:
            return False, "Access denied (403)"
        if 400 <= exc.code < 500:
            raw = exc.read().decode("utf-8", "replace")
            try:
                data = json.loads(raw)
                err = data.get("error", {}) if isinstance(data, dict) else {}
                etype = err.get("type", "")
                emsg = err.get("message", etype)
            except json.JSONDecodeError:
                etype = ""
                emsg = ""
            if etype in FATAL_PROVIDER_ERROR_TYPES:
                return False, f"Provider rejected: {emsg or etype}"
            return True, f"Reachable (HTTP {exc.code})"
        if 500 <= exc.code < 600:
            return False, f"Server error (HTTP {exc.code})"
        return False, f"Connection failed: unexpected HTTP status {exc.code}"
    except urllib.error.URLError as exc:
        return False, f"Connection failed: {exc.reason}"
    except TimeoutError:
        return False, "Connection failed: timed out"


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Claude Code provider switcher."""


@cli.command("init")
def init_cmd() -> None:
    """Create ccs config directories."""
    init_active_file()
    click.echo(f"ok dir:    {CCS_DIR}")
    click.echo("Set a provider:   ccs set <name> --base-url <url> --key <key>")


@cli.command("set")
@click.argument("name", required=False)
@click.option("--base-url")
@click.option("--key", "key_arg")
@click.option("--use-api-key", is_flag=True)
@click.option("--use-auth-token", is_flag=True)
@click.option("--model")
@click.option("--unset-model", is_flag=True)
@click.option("-e", "--env", "env_updates", multiple=True)
@click.option("--unset-env", "env_unsets", multiple=True)
def set_cmd(
    name: str | None,
    base_url: str | None,
    key_arg: str | None,
    use_api_key: bool,
    use_auth_token: bool,
    model: str | None,
    unset_model: bool,
    env_updates: tuple[str, ...],
    env_unsets: tuple[str, ...],
) -> None:
    """Create or update a provider."""
    ensure_dirs()
    if use_api_key and use_auth_token:
        die("--use-api-key and --use-auth-token cannot be used together")
    if name is None:
        name = prompt_required("Provider name")
    require_provider_name(name)

    options_provided = any(
        [
            base_url is not None,
            key_arg is not None,
            use_api_key,
            use_auth_token,
            model is not None,
            unset_model,
            bool(env_updates),
            bool(env_unsets),
        ]
    )
    for item in env_updates:
        if "=" not in item:
            die("-e/--env requires KEY=VALUE")
        validate_env_key(item.split("=", 1)[0])
    for item in env_unsets:
        validate_env_key(item)
        if item == "ANTHROPIC_BASE_URL":
            die("ANTHROPIC_BASE_URL cannot be removed; use --base-url to replace it")

    path = provider_file(name)
    created = not path.exists()
    conf = read_conf(path)
    env = provider_env(conf)
    current_auth = conf.get("auth") or AUTH_API_KEY
    current_key = conf.get("key") or ""
    current_base_url = env.get("ANTHROPIC_BASE_URL", "")
    current_model = env.get("ANTHROPIC_MODEL", "")

    auth = current_auth
    if use_api_key:
        auth = AUTH_API_KEY
    if use_auth_token:
        auth = AUTH_TOKEN

    if not options_provided:
        base_url = prompt_required("Base URL", current_base_url)
        auth = prompt_auth(current_auth)
        env_name = secret_env_name(auth)
        if created:
            key_arg = prompt_optional(f"Key for {env_name}", hide=True)
        else:
            key_arg = prompt_optional(
                f"Key for {env_name} (enter to keep current {masked_key(current_key)})", hide=True
            )
        model = prompt_optional("Model (optional)", current_model)
    elif created:
        if base_url is None:
            base_url = prompt_required("Base URL")
        if key_arg is None:
            key_arg = prompt_optional(f"Key for {secret_env_name(auth)}", hide=True)

    if key_arg == "-":
        key_arg = sys.stdin.readline().rstrip("\r\n")
    if key_arg:
        current_key = key_arg
    if not current_key:
        die("--key is required when creating a provider")

    if base_url is not None:
        env["ANTHROPIC_BASE_URL"] = base_url
    for item in env_unsets:
        env.pop(item, None)
    if unset_model:
        env.pop("ANTHROPIC_MODEL", None)
    if model:
        env["ANTHROPIC_MODEL"] = model
    for item in env_updates:
        env_key, env_value = item.split("=", 1)
        env[env_key] = env_value
    if not env.get("ANTHROPIC_BASE_URL"):
        die("ANTHROPIC_BASE_URL is required")

    write_provider(name, auth, current_key, env)
    action = "created" if created else "updated"
    if active_name() == name:
        apply_provider(name)
        click.echo(f"{action} {name} (active reapplied)")
    else:
        click.echo(f"{action} {name}")


@cli.command("use")
@click.argument("name")
@click.option("--no-verify", is_flag=True)
def use_cmd(name: str, no_verify: bool) -> None:
    """Switch active provider."""
    require_provider_name(name)
    path = provider_file(name)
    if not path.exists():
        die(f"no such provider: '{name}'")
    conf = read_conf(path)
    auth = conf.get("auth") or AUTH_API_KEY
    key = conf.get("key") or ""
    base_url = conf.get("ANTHROPIC_BASE_URL") or ""
    model = conf.get("ANTHROPIC_MODEL") or VERIFY_PROBE_MODEL

    if not no_verify:
        ok, msg = verify_request(base_url, key, model, auth)
        if not ok:
            click.echo(f"verify failed: {msg}")
            click.echo("Use --no-verify to switch anyway.")
            raise click.exceptions.Exit(1)
        click.echo(f"verify: {msg}")

    set_active(name)
    apply_provider(name)
    click.echo(f"switched -> {name}")
    click.echo(f"base_url: {base_url}")
    click.echo("Restart Claude Code session to pick up the new provider.")


@cli.command("verify")
@click.argument("name", required=False)
def verify_cmd(name: str | None) -> None:
    """Verify a provider."""
    target = name or active_name()
    if not target:
        die("no provider given and no active provider")
    require_provider_name(target)
    path = provider_file(target)
    if not path.exists():
        die(f"no such provider: '{target}'")
    conf = read_conf(path)
    ok, msg = verify_request(
        conf.get("ANTHROPIC_BASE_URL", ""),
        conf.get("key", ""),
        conf.get("ANTHROPIC_MODEL") or VERIFY_PROBE_MODEL,
        conf.get("auth") or AUTH_API_KEY,
    )
    click.echo(f"{target}: {msg}")
    if not ok:
        raise click.exceptions.Exit(1)


@cli.command("ls")
def list_cmd() -> None:
    """List providers."""
    ensure_dirs()
    active = active_name()
    table = Table(show_header=True)
    table.add_column("")
    table.add_column("Name")
    table.add_column("Secret env")
    table.add_column("Base URL")
    table.add_column("Key")
    found = False
    for path in sorted(PROVIDERS_DIR.glob("*.conf")):
        found = True
        name = path.stem
        conf = read_conf(path)
        table.add_row(
            "*" if name == active else "",
            name,
            secret_env_name(conf.get("auth") or AUTH_API_KEY),
            conf.get("ANTHROPIC_BASE_URL", ""),
            masked_key(conf.get("key", "")),
        )
    if found:
        console.print(table)
    else:
        click.echo("No providers yet. Try: ccs init && ccs set")


@cli.command("current")
def current_cmd() -> None:
    """Show active provider."""
    name = active_name()
    if not name:
        click.echo("No active provider")
        return
    path = provider_file(name)
    if not path.exists():
        die(f"active provider '{name}' is missing")
    click.echo(f"{name} -> {read_conf(path).get('ANTHROPIC_BASE_URL', '')}")


@cli.command("show")
@click.argument("name")
@click.option("--show-key", is_flag=True)
def show_cmd(name: str, show_key: bool) -> None:
    """Show provider details."""
    require_provider_name(name)
    path = provider_file(name)
    if not path.exists():
        die(f"no such provider: '{name}'")
    conf = read_conf(path)
    click.echo(f"{'name':<28} {name}")
    click.echo(f"{'active':<28} {'yes' if active_name() == name else 'no'}")
    click.echo(f"{'secret env':<28} {secret_env_name(conf.get('auth') or AUTH_API_KEY)}")
    key = conf.get("key", "")
    click.echo(f"{'key':<28} {key if show_key else masked_key(key)}")
    for env_key, env_value in provider_env(conf).items():
        click.echo(f"{env_key:<28} {env_value}")


@cli.command("rm")
@click.argument("name")
def rm_cmd(name: str) -> None:
    """Remove a provider."""
    require_provider_name(name)
    path = provider_file(name)
    if not path.exists():
        die(f"no such provider: '{name}'")
    path.unlink()
    if active_name() == name:
        clear_active()
        clear_provider_env()
    click.echo(f"removed {name}")


cli.add_command(list_cmd, "list")
cli.add_command(rm_cmd, "remove")

main = cli


if __name__ == "__main__":
    main()
