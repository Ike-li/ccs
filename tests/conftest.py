"""Pytest-wide HOME isolation for ccs filesystem tests.

ccs writes under ~/.config/ccs and ~/.claude/settings.json, so every test
gets a fresh tmp HOME automatically.
"""

import pytest


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path, monkeypatch):
    """Redirect $HOME to a per-test tmp directory.

    Both ``Path.home()`` (reads $HOME) and ``os.path.expanduser("~/...")``
    (also reads $HOME) follow this redirection. Subprocesses launched via
    ``subprocess.run(..., env={**os.environ, ...})`` inherit it too,
    because the autouse fixture mutates ``os.environ`` before the test
    fixtures build their env dict.
    """
    isolated_home = tmp_path / ".pytest_isolated_home"
    isolated_home.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(isolated_home))
    yield isolated_home
