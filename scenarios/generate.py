import time
from dataclasses import dataclass, field


@dataclass
class GeneratedTx:
    txid: str
    wallet: str
    scenario: str
    fingerprints: list = field(default_factory=list)


def generate(scenarios, driver, node, *, settle: float = 0.0, repeat: int = 1, sync=None) -> list[GeneratedTx]:
    """Generate `repeat` txs per scenario via `driver`; return labeled records.

    A scenario whose execution fails is skipped so one bad attempt doesn't abort the run.
    """
    results: list[GeneratedTx] = []
    for sc in scenarios:
        for _ in range(repeat):
            try:
                if sync is not None:
                    sync()
                txid = driver.execute(sc, node)
                node.mine_blocks(1)
                if settle:
                    time.sleep(settle)
            except Exception as exc:  # noqa: BLE001 - record and continue
                print(f"scenario {sc.label} failed: {exc}")
                continue
            results.append(GeneratedTx(txid, driver.name, sc.label, list(sc.fingerprints)))
    return results
