"""End-to-end runner for the labeled-transaction fingerprint pipeline.

Generates labeled regtest transactions from Electrum and Bitcoin Core, runs
Ishaana's detector over them, and reports per-wallet recall. Needs the Docker
stack (bitcoind + Fulcrum) up and, for detection, her repo cloned.

Usage:
    uv run python -m scenarios.run_e2e
    uv run python -m scenarios.run_e2e --repeat 3 --no-electrum
"""
import os

import click

from bitcoin.regtest import RegtestNode
from wallets.electrum import setup as esetup
from scenarios import (
    scenarios as scen,
    generate,
    electrum_driver,
    core_wallet,
    detect_bridge,
    validate,
    persist,
)


def _generate_electrum(node, repeat, coins):
    os.environ["ELECTRUM_WALLET"] = str(esetup.wallet_path())
    esetup.write_electrum_config()
    esetup.create_wallet_if_missing()
    node.fund_address(esetup.get_wallet_address(), coins)
    node.mine_blocks(1)
    with esetup.electrum_daemon():
        esetup._run_electrum("load_wallet", "-w", str(esetup.wallet_path()))
        electrum_driver.wait_for_coins()
        # sync waits for coins to appear; settle gives a freshly mined block time
        # to confirm so the next scenario does not build on an unconfirmed coin.
        from scenarios.drivers import ElectrumCliDriver
        return generate.generate(
            scen.SCENARIOS, ElectrumCliDriver(), node, repeat=repeat, settle=1.5, sync=electrum_driver.wait_for_coins
        )


def _safe_detect(txid):
    try:
        return detect_bridge.detect(txid)
    except Exception as exc:  # noqa: BLE001 - skip a tx the detector chokes on
        click.echo(f"  detect failed for {txid[:12]}: {exc}", err=True)
        return (set(), [])


@click.command()
@click.option("--repeat", default=2, show_default=True, help="Attempts per scenario")
@click.option("--coins", default=5.0, show_default=True, help="BTC to fund the Electrum wallet")
@click.option("--electrum/--no-electrum", default=True, help="Include the Electrum path")
@click.option("--out", default="out/e2e", show_default=True, help="Output directory")
def cli(repeat, coins, electrum, out):
    node = RegtestNode()
    node.create_or_load_wallet("dwf_funder")
    node.ensure_mature_coins()

    records = []
    if electrum:
        click.echo("Generating Electrum transactions...")
        records += _generate_electrum(node, repeat, coins)
    click.echo("Generating Bitcoin Core transactions...")
    records += core_wallet.generate_core(node, repeat=repeat)

    click.echo(f"Detecting {len(records)} transactions...")
    report = validate.build_report(records, _safe_detect)
    persist.save_dataset(records, report, out)

    click.echo(f"\nReport ({report.total} txs):")
    for wallet, m in sorted(report.per_wallet.items()):
        click.echo(f"  {wallet:<13} recall={m['recall']:.2f} unique={m['unique']:.2f} (n={m['count']})")
    click.echo(f"  misses: {len(report.misses)} | saved to {out}/")


if __name__ == "__main__":
    cli()
