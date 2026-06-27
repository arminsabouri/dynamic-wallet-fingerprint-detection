from scenarios.core_wallet import CORE_SCENARIOS
from scenarios.drivers import CoreDriver
from scenarios.generate import generate, GeneratedTx


class FakeRPC:
    def __init__(self): self.calls = []
    def sendtoaddress(self, *args):
        self.calls.append(("sendtoaddress", args)); return "core-txid"
    def sendmany(self, *args):
        self.calls.append(("sendmany", args)); return "core-multi-txid"


class FakeNode:
    def __init__(self): self.mined = 0
    def mine_blocks(self, n=1): self.mined += n; return ["b"]


def test_core_scenarios_cover_expected_labels():
    labels = {sc.label for sc in CORE_SCENARIOS}
    assert {"default", "send_p2pkh", "send_p2tr", "multi_output", "no_rbf"} <= labels


def test_generate_with_core_driver_labels_and_mines():
    rpc, node = FakeRPC(), FakeNode()
    out = generate(CORE_SCENARIOS, CoreDriver(rpc, lambda t: f"addr-{t}"), node)
    assert all(isinstance(r, GeneratedTx) and r.wallet == "Bitcoin Core" for r in out)
    assert len(out) == len(CORE_SCENARIOS)
    assert node.mined == len(CORE_SCENARIOS)
    assert any(c[0] == "sendmany" for c in rpc.calls)


def test_no_rbf_scenario_sets_replaceable_false():
    rpc = FakeRPC()
    sc = next(s for s in CORE_SCENARIOS if s.label == "no_rbf")
    sc.build(rpc, lambda t: "addr")
    name, args = rpc.calls[-1]
    assert name == "sendtoaddress"
    assert args[5] is False


def test_generate_with_core_driver_repeats():
    rpc, node = FakeRPC(), FakeNode()
    out = generate(CORE_SCENARIOS, CoreDriver(rpc, lambda t: f"addr-{t}"), node, repeat=2)
    assert len(out) == 2 * len(CORE_SCENARIOS)
    assert node.mined == 2 * len(CORE_SCENARIOS)
