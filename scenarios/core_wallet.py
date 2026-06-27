from dataclasses import dataclass, field

RECIPIENT_WALLET = "dwf_recipient"


@dataclass
class CoreScenario:
    label: str
    build: object  # callable(rpc, addr_fn) -> txid
    fingerprints: list = field(default_factory=list)


def _default(rpc, addr):
    return rpc.sendtoaddress(addr("bech32"), 0.005)


def _send(addr_type):
    def build(rpc, addr):
        return rpc.sendtoaddress(addr(addr_type), 0.005)
    return build


def _multi(rpc, addr):
    return rpc.sendmany("", {addr("legacy"): 0.003, addr("bech32"): 0.003, addr("bech32m"): 0.003})


def _no_rbf(rpc, addr):
    return rpc.sendtoaddress(addr("bech32"), 0.005, "", "", False, False)


def _manual_feerate(rpc, addr):
    return rpc.sendtoaddress(addr("bech32"), 0.005, "", "", False, True, None, "unset", False, 2.0)


# Detector's exact output strings (same vocabulary as Electrum); empty where the
# scenario's trait produces no signal.
CORE_SCENARIOS = [
    CoreScenario("default", _default, []),
    CoreScenario("send_p2pkh", _send("legacy"), []),
    CoreScenario("send_p2wpkh", _send("bech32"), []),
    CoreScenario("send_p2tr", _send("bech32m"), ["Sends to taproot address"]),
    CoreScenario("multi_output", _multi, ["More than 2 outputs"]),
    CoreScenario("no_rbf", _no_rbf, ["does not signal RBF"]),
    CoreScenario("manual_feerate", _manual_feerate, []),
]


def generate_core(node, *, settle: float = 0.0, repeat: int = 1):
    from bitcoin.regtest import RegtestNode
    from scenarios.generate import generate
    from scenarios.drivers import CoreDriver

    node.create_or_load_wallet(RECIPIENT_WALLET)
    recipient = RegtestNode(RECIPIENT_WALLET)
    node.create_or_load_wallet("dwf_funder")
    driver = CoreDriver(node.rpc(), lambda t: recipient.rpc().getnewaddress("", t))
    return generate(CORE_SCENARIOS, driver, node, settle=settle, repeat=repeat)
