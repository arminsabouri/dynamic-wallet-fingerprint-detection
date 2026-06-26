import os
from pathlib import Path

import pytest

from scenarios import detect_bridge


def test_ensure_config_writes_regtest_ini(tmp_path):
    detect_bridge._ensure_config(str(tmp_path))
    cfg = (tmp_path / "rpc_config.ini").read_text()
    assert "127.0.0.1:18443" in cfg
    assert "RPCUSER = bitcoin" in cfg


def _ishaana_available():
    return Path(os.getenv("ISHAANA_REPO", str(Path.home() / "wallet-fingerprinting"))).exists()


@pytest.mark.skipif(
    not _ishaana_available() or os.getenv("DWF_NETWORK_TESTS") != "1",
    reason="needs Ishaana repo + running regtest Core (set DWF_NETWORK_TESTS=1)",
)
def test_detect_on_real_regtest_tx():
    txid = "f005597602d07c5247eb34dbaa6cfb82056d54eba11b8762d22bd9508acce3af"
    wallets, fingerprints = detect_bridge.detect(txid)
    assert "Electrum" in wallets
    assert isinstance(fingerprints, list)
