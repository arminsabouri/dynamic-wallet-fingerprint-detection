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
