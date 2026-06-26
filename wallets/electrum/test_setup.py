import json
import pytest
from pathlib import Path

from wallets.electrum import setup


def test_electrum_bin_env_override(monkeypatch):
    monkeypatch.setenv("ELECTRUM_BIN", "/tmp/x/run_electrum")
    assert setup.electrum_bin() == "/tmp/x/run_electrum"


def test_electrum_bin_default_is_repo_sibling(monkeypatch):
    monkeypatch.delenv("ELECTRUM_BIN", raising=False)
    repo_root = Path(setup.__file__).resolve().parents[2]
    expected = str(repo_root.parent / "electrum" / "run_electrum")
    assert setup.electrum_bin() == expected
    # the original bug returned an unnormalized path containing ".."
    assert ".." not in setup.electrum_bin()


def test_electrum_python_override(monkeypatch):
    monkeypatch.setenv("ELECTRUM_PYTHON", "/tmp/py")
    assert setup.electrum_python() == "/tmp/py"


def test_electrum_python_default_is_venv_beside_bin(monkeypatch):
    monkeypatch.delenv("ELECTRUM_PYTHON", raising=False)
    monkeypatch.setenv("ELECTRUM_BIN", "/opt/electrum/run_electrum")
    assert setup.electrum_python() == "/opt/electrum/venv/bin/python"


def test_electrum_cmd_is_python_then_bin(monkeypatch):
    monkeypatch.setenv("ELECTRUM_PYTHON", "/tmp/py")
    monkeypatch.setenv("ELECTRUM_BIN", "/opt/electrum/run_electrum")
    assert setup.electrum_cmd() == ["/tmp/py", "/opt/electrum/run_electrum"]


def _electrum_available():
    return Path(setup.electrum_python()).exists() and Path(setup.electrum_bin()).exists()


@pytest.mark.skipif(not _electrum_available(), reason="Electrum source/venv not installed")
def test_create_wallet_and_get_address(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "WALLET_NAME", "dwf_pytest")
    monkeypatch.setattr(setup, "electrum_wallet_dir", lambda: tmp_path)
    setup.create_wallet_if_missing()
    assert (tmp_path / "dwf_pytest").exists()
    addr = setup.get_wallet_address()
    assert addr.startswith("bcrt1")


def test_write_electrum_config_pins_version_and_tcp_server(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "electrum_config_dir", lambda: tmp_path)
    setup.write_electrum_config("127.0.0.1", 50001)
    cfg = json.loads((tmp_path / "config").read_text())
    # config_version pins Electrum past the migration that rewrites the server
    # to SSL, which a plain-TCP Fulcrum would refuse.
    assert cfg["config_version"] == 3
    assert cfg["server"] == "127.0.0.1:50001:t"
    assert cfg["oneserver"] is True


class _FakeRun:
    def __init__(self, stdout="", stderr=""):
        self.stdout = stdout
        self.stderr = stderr


def test_electrum_daemon_recovers_from_stale_lock(monkeypatch):
    calls = []

    def fake_run(*args, **_kw):
        calls.append(args)
        if args == ("daemon", "-d"):
            first = calls.count(("daemon", "-d")) == 1
            return _FakeRun("Daemon already running (lockfile detected)." if first
                            else "starting daemon (PID 1)")
        if args[0] == "list_wallets":
            return _FakeRun("Daemon not running; try 'electrum daemon -d'")
        return _FakeRun()

    cleared = []
    monkeypatch.setattr(setup, "_run_electrum", fake_run)
    monkeypatch.setattr(setup, "_clear_daemon_lock", lambda: cleared.append(True))

    with setup.electrum_daemon():
        pass

    assert cleared == [True]                     # stale lock detected and cleared
    assert calls.count(("daemon", "-d")) == 2    # daemon retried after clearing
    assert ("stop",) in calls                    # retry started it, so we stop it


def test_electrum_daemon_leaves_live_daemon_untouched(monkeypatch):
    calls = []

    def fake_run(*args, **_kw):
        calls.append(args)
        if args == ("daemon", "-d"):
            return _FakeRun("Daemon already running (lockfile detected).")
        if args[0] == "list_wallets":
            return _FakeRun("[]")                 # daemon answers, so it is alive
        return _FakeRun()

    cleared = []
    monkeypatch.setattr(setup, "_run_electrum", fake_run)
    monkeypatch.setattr(setup, "_clear_daemon_lock", lambda: cleared.append(True))

    with setup.electrum_daemon():
        pass

    assert cleared == []              # a live daemon's lockfile is never cleared
    assert ("stop",) not in calls     # we did not start it, so we must not stop it
