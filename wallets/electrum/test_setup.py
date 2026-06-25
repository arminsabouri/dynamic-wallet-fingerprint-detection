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
