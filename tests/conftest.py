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
    yield isolated_home
