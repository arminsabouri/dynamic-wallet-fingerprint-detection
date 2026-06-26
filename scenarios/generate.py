import time
from dataclasses import dataclass, field

from scenarios import electrum_driver


@dataclass
class GeneratedTx:
    txid: str
    wallet: str
    scenario: str
    fingerprints: list = field(default_factory=list)


def generate(node, scenarios, *, driver=electrum_driver, settle: float = 0.0, repeat: int = 1, sync=None) -> list[GeneratedTx]:
    """Generate `repeat` Electrum txs per scenario on regtest; return labeled records.

    A scenario whose payto/broadcast fails is skipped so one bad attempt does not abort
    the run. ``sync``, if given, is called before each attempt to block until the wallet
    has synced its coins (see electrum_driver.wait_for_coins); ``settle`` seconds are
    slept after mining each block.
    """
    results: list[GeneratedTx] = []
    for sc in scenarios:
        for _ in range(repeat):
            try:
                if sync is not None:
                    sync()
                if sc.build is not None:
                    tx_hex = sc.build(node, driver)
                else:
                    dest = node.get_new_address("", sc.addr_type or "bech32")
                    tx_hex = driver.payto(dest, sc.amount, **sc.opts)
                txid = driver.broadcast(tx_hex)
                node.mine_blocks(1)
                if settle:
                    time.sleep(settle)
            except Exception as exc:  # noqa: BLE001 - record and continue
                print(f"scenario {sc.label} failed: {exc}")
                continue
            results.append(GeneratedTx(txid, "Electrum", sc.label, list(sc.fingerprints)))
    return results
