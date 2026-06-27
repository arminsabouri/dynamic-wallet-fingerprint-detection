from scenarios import drivers
from scenarios.scenarios import Scenario
from scenarios.core_wallet import CoreScenario


class FakeElectrum:
    def __init__(self): self.calls = []
    def payto(self, dest, amount, **opts):
        self.calls.append(("payto", dest, amount, opts)); return "HEX"
    def broadcast(self, tx_hex): return f"txid-{tx_hex}"


class FakeNode:
    def get_new_address(self, label="", addr_type="bech32"): return f"addr-{addr_type}"


def test_electrum_driver_declarative_scenario_paytos_and_broadcasts():
    d = drivers.ElectrumCliDriver(driver=FakeElectrum())
    sc = Scenario("no_rbf", "bech32", 0.005, {"rbf": False})
    txid = d.execute(sc, FakeNode())
    assert txid == "txid-HEX"
    assert d._d.calls[0] == ("payto", "addr-bech32", 0.005, {"rbf": False})
    assert d.name == "Electrum"


def test_electrum_driver_runs_build_hook():
    built = {}
    def builder(node, driver):
        built["yes"] = True; return "CUSTOM"
    d = drivers.ElectrumCliDriver(driver=FakeElectrum())
    sc = Scenario("custom", None, None, {}, [], build=builder)
    assert d.execute(sc, FakeNode()) == "txid-CUSTOM"
    assert built["yes"] is True


def test_core_driver_calls_build_with_rpc_and_addr_fn():
    seen = {}
    def build(rpc, addr_fn):
        seen["rpc"] = rpc; seen["addr"] = addr_fn("legacy"); return "core-txid"
    d = drivers.CoreDriver("RPC", lambda t: f"a-{t}")
    sc = CoreScenario("x", build, [])
    assert d.execute(sc, FakeNode()) == "core-txid"
    assert seen["rpc"] == "RPC" and seen["addr"] == "a-legacy"
    assert d.name == "Bitcoin Core"
