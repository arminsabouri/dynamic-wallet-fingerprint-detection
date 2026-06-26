import os
from pathlib import Path

import pytest

from scenarios import core_wallet, detect_bridge, validate


def _ready():
    ishaana = Path(os.getenv("ISHAANA_REPO", str(Path.home() / "wallet-fingerprinting"))).exists()
    return ishaana and os.getenv("DWF_NETWORK_TESTS") == "1"


@pytest.mark.skipif(not _ready(), reason="needs Ishaana repo + regtest Core (set DWF_NETWORK_TESTS=1)")
def test_core_pipeline_detects_every_tx():
    # Core generation is deterministic (no Electrum/Fulcrum sync), so the
    # detector must place Bitcoin Core in every candidate set. This guards the
    # generate -> detect -> report path against regressions in any of them.
    from bitcoin.regtest import RegtestNode

    node = RegtestNode()
    node.create_or_load_wallet("dwf_funder")
    node.ensure_mature_coins()
    records = core_wallet.generate_core(node, repeat=1)
    assert records, "no Core transactions generated"
    report = validate.build_report(records, detect_bridge.detect)
    assert report.per_wallet["Bitcoin Core"]["recall"] == 1.0
