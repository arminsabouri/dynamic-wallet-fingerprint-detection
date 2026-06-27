"""One-shot smoke for the vision agent.

Sets up the regtest Electrum wallet, snapshots its history, lets the agent
drive the GUI, then isolates the transactions the agent produced and runs the
detector over them so you can compare what the GUI made against what the
detector sees.

Cost is bounded by your Anthropic console spend limit (the agent loop has no
internal cap). macOS: grant the terminal Accessibility + Screen Recording,
then run with DWF_DEBUG_DISPLAY=1 (uses the real screen instead of Xvfb).

    DWF_DEBUG_DISPLAY=1 uv run python smoke_agent.py --coins 1
"""
import json
import os

import click

from bitcoin.regtest import RegtestNode
from wallets.electrum import setup as esetup, launch
from scenarios import electrum_driver, detect_bridge, analyze, compare
from harness import display


def _history_snapshot():
    with esetup.electrum_daemon():
        esetup._run_electrum("load_wallet", "-w", str(esetup.wallet_path()))
        electrum_driver.wait_for_coins()
        return electrum_driver.history()


@click.command()
@click.option("--coins", default=1.0, show_default=True, help="BTC to fund the wallet")
@click.option("--out", default="out/agent_smoke", show_default=True)
def cli(coins, out):
    os.environ["ELECTRUM_WALLET"] = str(esetup.wallet_path())
    node = RegtestNode()
    node.create_or_load_wallet("dwf_funder")
    node.ensure_mature_coins()
    import bootstrap
    bootstrap.prepare_wallet(node, coins=coins)

    before = set(_history_snapshot())  # daemon stops here, freeing the wallet for the GUI

    display.start()
    launch.start()
    try:
        from agent import WalletAgent, Session

        WalletAgent(node, Session()).run()
    finally:
        launch.stop()
        display.stop()

    new_txids = [t for t in _history_snapshot() if t not in before]
    report = analyze.analyze_txids(new_txids, detect_bridge.detect)
    cov = compare.coverage(set(report.fingerprint_counts))

    os.makedirs(out, exist_ok=True)
    json.dump(
        {
            "txids": new_txids,
            "wallet_counts": report.wallet_counts,
            "fingerprint_counts": report.fingerprint_counts,
            "per_tx": report.per_tx,
            "coverage": {
                "rate": cov.rate,
                "covered": sorted(cov.covered),
                "missing": sorted(cov.missing),
            },
        },
        open(f"{out}/analysis.json", "w"),
        indent=2,
    )
    click.echo(f"\nAgent produced {len(new_txids)} transactions -> {out}/analysis.json")
    click.echo(f"  detected wallets:      {report.wallet_counts}")
    click.echo(f"  detected fingerprints: {report.fingerprint_counts}")
    click.echo(f"  baseline coverage:     {cov.rate:.2f}  (missing: {sorted(cov.missing)})")


if __name__ == "__main__":
    cli()
