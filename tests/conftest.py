"""Pytest-wide HOME isolation for ccs filesystem tests.

ccs writes under ~/.config/ccs and ~/.claude/settings.json, so every test
gets a fresh tmp HOME automatically.
"""

import pytest


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    """Redirect $HOME to a per-test tmp directory and drop path overrides.

    Both ``Path.home()`` (reads $HOME) and ``os.path.expanduser("~/...")``
    (also reads $HOME) follow this redirection. Subprocesses launched via
    ``subprocess.run(..., env={**os.environ, ...})`` inherit it too,
    because the autouse fixture mutates ``os.environ`` before the test
    fixtures build their env dict.

    CCS_DIR and CLAUDE_SETTINGS_FILE override the HOME-derived paths in
    bin/ccs, so a developer or CI shell that exports either one would make
    the suite write to the real config despite the tmp HOME. Clear them
    here so HOME redirection is the single source of truth.
    """
    isolated_home = tmp_path / ".pytest_isolated_home"
    isolated_home.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(isolated_home))
    monkeypatch.delenv("CCS_DIR", raising=False)
    monkeypatch.delenv("CLAUDE_SETTINGS_FILE", raising=False)
    # Keep host git config out of the sandbox: ccs runs `git check-ignore`
    # and tests run `git init`, both of which read the developer's
    # global/system config. A host excludesfile that happens to ignore
    # *.local.json would silently flip the gitignore-guard tests.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("GIT_DIR", raising=False)
    # ccs's make_temp honours TMPDIR; point it into the sandbox so die
    # paths cannot strand ccs-* temp files in the real /tmp.
    tmp_dir = tmp_path / ".pytest_tmpdir"
    tmp_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("TMPDIR", str(tmp_dir))
    yield isolated_home
