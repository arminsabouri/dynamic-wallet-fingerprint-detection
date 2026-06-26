from dataclasses import dataclass, field


@dataclass
class Scenario:
    label: str
    addr_type: str | None   # "legacy" | "bech32" | "bech32m" | None
    amount: object
    opts: dict = field(default_factory=dict)
    fingerprints: list = field(default_factory=list)
    build: object = None   # optional callable (node, driver) -> tx_hex


SCENARIOS = [
    Scenario("default", "bech32", 0.005, {}, ["anti_fee_sniping", "bip69", "low_r", "rbf"]),
    Scenario("send_p2pkh", "legacy", 0.005, {}, ["output_p2pkh"]),
    Scenario("send_p2wpkh", "bech32", 0.005, {}, ["output_p2wpkh"]),
    Scenario("send_p2tr", "bech32m", 0.005, {}, ["output_p2tr"]),
    Scenario("no_rbf", "bech32", 0.005, {"rbf": False}, ["no_rbf"]),
    Scenario("manual_feerate", "bech32", 0.005, {"feerate": 5}, ["manual_feerate"]),
]


def _coin_id(driver):
    coin = driver.listunspent()[0]
    return f"{coin['prevout_hash']}:{coin['prevout_n']}"


def _build_multi_output(node, driver):
    outs = [(node.get_new_address("", "bech32"), 0.003) for _ in range(3)]
    return driver.paytomany(outs)


def _build_coin_control(node, driver):
    dest = node.get_new_address("", "bech32")
    return driver.payto(dest, 0.003, from_coins=_coin_id(driver))


def _build_changeless(node, driver):
    dest = node.get_new_address("", "bech32")
    return driver.payto(dest, "!", from_coins=_coin_id(driver))


SCENARIOS += [
    Scenario("multi_output", None, None, {}, ["multi_output"], build=_build_multi_output),
    Scenario("coin_control", None, None, {}, ["coin_control"], build=_build_coin_control),
    Scenario("changeless", None, None, {}, ["no_change"], build=_build_changeless),
]
