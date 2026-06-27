"""Deterministic generation drivers: turn one scenario into a broadcast txid.

The GUI agent is deliberately not a Driver: it explores, it doesn't run scenarios.
"""
from scenarios import electrum_driver as _electrum


class ElectrumCliDriver:
    name = "Electrum"

    def __init__(self, driver=_electrum):
        self._d = driver

    def execute(self, sc, node) -> str:
        if sc.build is not None:
            tx_hex = sc.build(node, self._d)
        else:
            dest = node.get_new_address("", sc.addr_type or "bech32")
            tx_hex = self._d.payto(dest, sc.amount, **sc.opts)
        return self._d.broadcast(tx_hex)


class CoreDriver:
    name = "Bitcoin Core"

    def __init__(self, rpc, addr_fn):
        self._rpc = rpc
        self._addr = addr_fn

    def execute(self, sc, node) -> str:
        return sc.build(self._rpc, self._addr)
