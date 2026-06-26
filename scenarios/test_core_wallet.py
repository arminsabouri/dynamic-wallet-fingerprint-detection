from scenarios.core_wallet import CORE_SCENARIOS, run_core_scenarios
from scenarios.generate import GeneratedTx


class FakeRPC:
    def __init__(self):
        self.calls = []

    def sendtoaddress(self, *args):
        self.calls.append(("sendtoaddress", args))
        return "core-txid"

    def sendmany(self, *args):
        self.calls.append(("sendmany", args))
        return "core-multi-txid"


def test_core_scenarios_cover_expected_labels():
    labels = {sc.label for sc in CORE_SCENARIOS}
    assert {"default", "send_p2pkh", "send_p2tr", "multi_output", "no_rbf"} <= labels


def test_run_core_scenarios_labels_and_mines():
    rpc = FakeRPC()
    mined = []
    out = run_core_scenarios(rpc, lambda t: f"addr-{t}", lambda: mined.append(1))
    assert all(isinstance(r, GeneratedTx) and r.wallet == "Bitcoin Core" for r in out)
    assert len(out) == len(CORE_SCENARIOS)
    assert len(mined) == len(CORE_SCENARIOS)
    assert any(call[0] == "sendmany" for call in rpc.calls)


def test_no_rbf_scenario_sets_replaceable_false():
    rpc = FakeRPC()
    sc = next(s for s in CORE_SCENARIOS if s.label == "no_rbf")
    sc.build(rpc, lambda t: "addr")
    name, args = rpc.calls[-1]
    assert name == "sendtoaddress"
    assert args[5] is False


def test_run_core_scenarios_repeats():
    rpc = FakeRPC()
    mined = []
    out = run_core_scenarios(rpc, lambda t: f"addr-{t}", lambda: mined.append(1), repeat=2)
    assert len(out) == 2 * len(CORE_SCENARIOS)
    assert len(mined) == 2 * len(CORE_SCENARIOS)
