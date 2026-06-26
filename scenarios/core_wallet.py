import time
from dataclasses import dataclass, field

from scenarios.generate import GeneratedTx

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


CORE_SCENARIOS = [
    CoreScenario("default", _default, ["default"]),
    CoreScenario("send_p2pkh", _send("legacy"), ["output_p2pkh"]),
    CoreScenario("send_p2wpkh", _send("bech32"), ["output_p2wpkh"]),
    CoreScenario("send_p2tr", _send("bech32m"), ["output_p2tr"]),
    CoreScenario("multi_output", _multi, ["multi_output"]),
    CoreScenario("no_rbf", _no_rbf, ["no_rbf"]),
    CoreScenario("manual_feerate", _manual_feerate, ["manual_feerate"]),
]


def run_core_scenarios(send_rpc, addr_fn, mine, *, settle: float = 0.0, repeat: int = 1, scenarios=CORE_SCENARIOS):
    results = []
    for sc in scenarios:
        for _ in range(repeat):
            try:
                txid = sc.build(send_rpc, addr_fn)
                mine()
                if settle:
                    time.sleep(settle)
            except Exception as exc:  # noqa: BLE001 - record and continue
                print(f"core scenario {sc.label} failed: {exc}")
                continue
            results.append(GeneratedTx(txid, "Bitcoin Core", sc.label, list(sc.fingerprints)))
    return results


def generate_core(node, *, settle: float = 0.0, repeat: int = 1):
    from bitcoin.regtest import RegtestNode

    node.create_or_load_wallet(RECIPIENT_WALLET)
    recipient = RegtestNode(RECIPIENT_WALLET)
    node.create_or_load_wallet("dwf_funder")
    return run_core_scenarios(
        node.rpc(),
        lambda t: recipient.rpc().getnewaddress("", t),
        lambda: node.mine_blocks(1),
        settle=settle,
        repeat=repeat,
    )
