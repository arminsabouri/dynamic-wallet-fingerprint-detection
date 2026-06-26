from scenarios.scenarios import Scenario, SCENARIOS


def test_scenarios_are_well_formed():
    assert len(SCENARIOS) >= 6
    labels = [s.label for s in SCENARIOS]
    assert len(labels) == len(set(labels))  # unique labels
    for s in SCENARIOS:
        assert isinstance(s, Scenario)
        assert s.addr_type in {"legacy", "bech32", "bech32m", None}
        assert s.amount is not None or s.build is not None
        assert isinstance(s.opts, dict)


def test_new_build_scenarios_present():
    by_label = {s.label: s for s in SCENARIOS}
    for label in ("multi_output", "coin_control", "changeless"):
        assert label in by_label
        assert callable(by_label[label].build)


class _FakeNode:
    def get_new_address(self, label="", addr_type="bech32"):
        return f"addr-{addr_type}"


class _FakeDriver:
    def __init__(self):
        self.last = None

    def payto(self, dest, amount, **opts):
        self.last = ("payto", dest, amount, opts)
        return "HEX"

    def paytomany(self, outputs, **opts):
        self.last = ("paytomany", list(outputs), opts)
        return "HEX"

    def listunspent(self):
        return [{"prevout_hash": "aa", "prevout_n": 2, "value": "1.0"}]


def test_changeless_build_uses_coin_and_max():
    from scenarios.scenarios import _build_changeless
    drv = _FakeDriver()
    _build_changeless(_FakeNode(), drv)
    kind, dest, amount, opts = drv.last
    assert kind == "payto" and amount == "!"
    assert opts["from_coins"] == "aa:2"


def test_multi_output_build_makes_three_outputs():
    from scenarios.scenarios import _build_multi_output
    drv = _FakeDriver()
    _build_multi_output(_FakeNode(), drv)
    kind, outputs, opts = drv.last
    assert kind == "paytomany" and len(outputs) == 3
