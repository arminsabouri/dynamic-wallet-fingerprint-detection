from dataclasses import dataclass, field


@dataclass
class Scenario:
    label: str
    addr_type: str | None   # "legacy" | "bech32" | "bech32m" | None
    amount: object
    opts: dict = field(default_factory=dict)
    fingerprints: list = field(default_factory=list)
    build: object = None   # optional callable (node, driver) -> tx_hex


# Fingerprints are the detector's exact output strings (one shared vocabulary);
# empty where the scenario's trait produces no on-chain signal the detector reports.
SCENARIOS = [
    Scenario("default", "bech32", 0.005, {}, ["Anti-fee-sniping", "BIP-69 followed by outputs", "Low r signatures only", "signals RBF"]),
    Scenario("send_p2pkh", "legacy", 0.005, {}, []),
    Scenario("send_p2wpkh", "bech32", 0.005, {}, []),
    Scenario("send_p2tr", "bech32m", 0.005, {}, ["Sends to taproot address"]),
    Scenario("no_rbf", "bech32", 0.005, {"rbf": False}, ["does not signal RBF"]),
    Scenario("manual_feerate", "bech32", 0.005, {"feerate": 5}, []),
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
    Scenario("multi_output", None, None, {}, ["More than 2 outputs"], build=_build_multi_output),
    Scenario("coin_control", None, None, {}, [], build=_build_coin_control),
    Scenario("changeless", None, None, {}, [], build=_build_changeless),
]
