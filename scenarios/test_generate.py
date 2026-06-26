from scenarios.generate import generate, GeneratedTx
from scenarios.scenarios import Scenario


class FakeNode:
    def __init__(self):
        self.mined = 0

    def get_new_address(self, label="", addr_type="bech32"):
        return f"addr-{addr_type}"

    def mine_blocks(self, n=1):
        self.mined += n
        return ["blockhash"]


class FakeDriver:
    def __init__(self):
        self.calls = []

    def payto(self, dest, amount, **opts):
        self.calls.append((dest, amount, opts))
        return "RAWHEX"

    def broadcast(self, tx_hex):
        return f"txid-for-{tx_hex}"


def test_generate_runs_each_scenario():
    node = FakeNode()
    driver = FakeDriver()
    scenarios = [
        Scenario("default", "bech32", 0.005, {}),
        Scenario("no_rbf", "bech32", 0.005, {"rbf": False}),
    ]
    out = generate(node, scenarios, driver=driver)
    assert [r.scenario for r in out] == ["default", "no_rbf"]
    assert all(isinstance(r, GeneratedTx) and r.wallet == "Electrum" for r in out)
    assert out[0].txid == "txid-for-RAWHEX"
    assert node.mined == 2
    assert driver.calls[1][2] == {"rbf": False}


def test_generate_continues_past_a_failing_scenario():
    node = FakeNode()

    class FlakyDriver(FakeDriver):
        def payto(self, dest, amount, **opts):
            if opts.get("feerate") == 999:
                raise RuntimeError("bad feerate")
            return super().payto(dest, amount, **opts)

    scenarios = [
        Scenario("bad", "bech32", 0.005, {"feerate": 999}),
        Scenario("good", "bech32", 0.005, {}),
    ]
    out = generate(node, scenarios, driver=FlakyDriver())
    assert [r.scenario for r in out] == ["good"]


def test_generate_uses_build_hook():
    from scenarios.generate import generate
    from scenarios.scenarios import Scenario

    calls = {}

    class Node:
        def mine_blocks(self, n=1):
            return ["b"]

    class Driver:
        def broadcast(self, h):
            return "txid"

    def builder(node, driver):
        calls["built"] = True
        return "CUSTOMHEX"

    sc = Scenario("custom", None, None, {}, [], build=builder)
    out = generate(Node(), [sc], driver=Driver())
    assert calls.get("built") is True
    assert out[0].txid == "txid"


def test_generate_repeats_each_scenario():
    from scenarios.generate import generate
    from scenarios.scenarios import Scenario

    class Node:
        def __init__(self):
            self.mined = 0

        def mine_blocks(self, n=1):
            self.mined += n
            return ["b"]

    class Driver:
        def __init__(self):
            self.n = 0

        def broadcast(self, h):
            self.n += 1
            return f"txid{self.n}"

    def builder(node, driver):
        return "HEX"

    node = Node()
    sc = Scenario("custom", None, None, {}, [], build=builder)
    out = generate(node, [sc], driver=Driver(), repeat=3)
    assert len(out) == 3
    assert all(r.scenario == "custom" for r in out)
    assert node.mined == 3
