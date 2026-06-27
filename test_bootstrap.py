# test_bootstrap.py
import bootstrap


class _Node:
    def __init__(self):
        self.funded = None
        self.mined = 0

    def fund_address(self, addr, coins):
        self.funded = (addr, coins)
        return "txid"

    def mine_blocks(self, n=1):
        self.mined += n
        return ["blk"]


def test_prepare_wallet_configures_funds_and_returns_address(monkeypatch):
    calls = []
    monkeypatch.setattr(bootstrap.esetup, "write_electrum_config", lambda *a, **k: calls.append("config"))
    monkeypatch.setattr(bootstrap.esetup, "create_wallet_if_missing", lambda: calls.append("create"))
    monkeypatch.setattr(bootstrap.esetup, "get_wallet_address", lambda: "bcrt1qfake")
    monkeypatch.setattr(bootstrap.time, "sleep", lambda *_: None)

    node = _Node()
    addr = bootstrap.prepare_wallet(node, coins=2.0)

    assert addr == "bcrt1qfake"
    assert node.funded == ("bcrt1qfake", 2.0)
    assert node.mined == 1
    assert calls == ["config", "create"]
