from dataclasses import dataclass, field

from scenarios.generate import generate, GeneratedTx


@dataclass
class _Sc:
    label: str
    fingerprints: list = field(default_factory=list)


class FakeNode:
    def __init__(self): self.mined = 0
    def mine_blocks(self, n=1): self.mined += n; return ["b"]


class FakeDriver:
    name = "Electrum"
    def __init__(self): self.executed = []
    def execute(self, sc, node):
        self.executed.append(sc.label); return f"txid-{sc.label}"


def test_generate_runs_each_scenario_and_mines():
    node, driver = FakeNode(), FakeDriver()
    out = generate([_Sc("default"), _Sc("no_rbf")], driver, node)
    assert [r.scenario for r in out] == ["default", "no_rbf"]
    assert all(isinstance(r, GeneratedTx) and r.wallet == "Electrum" for r in out)
    assert out[0].txid == "txid-default"
    assert node.mined == 2


def test_generate_continues_past_a_failing_scenario():
    node = FakeNode()
    class Flaky:
        name = "Electrum"
        def execute(self, sc, node):
            if sc.label == "bad": raise RuntimeError("boom")
            return "ok"
    out = generate([_Sc("bad"), _Sc("good")], Flaky(), node)
    assert [r.scenario for r in out] == ["good"]


def test_generate_calls_sync_before_each_attempt():
    node, driver = FakeNode(), FakeDriver()
    syncs = []
    generate([_Sc("a"), _Sc("b")], driver, node, sync=lambda: syncs.append(len(driver.executed)))
    assert syncs == [0, 1]


def test_generate_repeats_each_scenario():
    node, driver = FakeNode(), FakeDriver()
    out = generate([_Sc("x")], driver, node, repeat=3)
    assert len(out) == 3 and node.mined == 3
