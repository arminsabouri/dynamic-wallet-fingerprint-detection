"""CLI launcher for the wallet enumeration agent.

Usage:
    uv run python run.py
    DWF_DEBUG_DISPLAY=1 uv run python run.py   # keep display visible
"""

import os
import sys
import time
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()


@click.command()
@click.option("--no-docker-check", is_flag=True, help="Skip Docker/Fulcrum readiness check")
@click.option("--coins", default=5.0, show_default=True, help="BTC to pre-fund the wallet with")
def cli(no_docker_check, coins):
    if not os.getenv("ANTHROPIC_API_KEY"):
        click.echo("Error: ANTHROPIC_API_KEY is not set. Add it to .env or your environment.", err=True)
        sys.exit(1)

    # -- Check Docker stack --
    if not no_docker_check:
        _check_docker()

    # -- Bitcoin Core connection --
    from bitcoin.regtest import RegtestNode
    click.echo("Connecting to Bitcoin Core regtest...")
    node = RegtestNode()
    node.create_or_load_wallet("dwf_funder")
    node.ensure_mature_coins()
    click.echo(f"  Height: {node.get_block_count()} blocks")

    # -- Electrum wallet setup --
    from wallets.electrum.setup import (
        write_electrum_config,
        create_wallet_if_missing,
        get_wallet_address,
    )
    fulcrum_host = os.getenv("FULCRUM_HOST", "127.0.0.1")
    fulcrum_port = int(os.getenv("FULCRUM_PORT", "50001"))
    write_electrum_config(fulcrum_host, fulcrum_port)
    create_wallet_if_missing()
    wallet_addr = get_wallet_address()
    click.echo(f"  Wallet address: {wallet_addr}")

    # -- Pre-fund --
    click.echo(f"  Funding wallet with {coins} BTC...")
    node.fund_address(wallet_addr, coins)
    node.mine_blocks(1)
    time.sleep(3.0)  # Fulcrum indexing

    # -- Virtual display --
    from harness import display
    disp = display.start()
    click.echo(f"  Display: {disp}")

    # -- Launch Electrum --
    from wallets.electrum import launch
    click.echo("Launching Electrum...")
    launch.start()
    click.echo("  Electrum ready.")

    # -- Run agent --
    from agent import WalletAgent, Session
    session = Session()
    agent = WalletAgent(node, session)

    try:
        agent.run()
    except KeyboardInterrupt:
        click.echo("\nInterrupted.")
        session.log = lambda e: None  # silence further logging
    finally:
        launch.stop()
        display.stop()

    click.echo(f"\nDone. Log: {session.log_path}")


def _check_docker():
    import subprocess
    result = subprocess.run(
        ["docker", "compose", "ps", "--services", "--filter", "status=running"],
        capture_output=True, text=True,
    )
    running = result.stdout.strip().splitlines()
    needed = {"bitcoin-core", "fulcrum"}
    missing = needed - set(running)
    if missing:
        click.echo(f"Docker services not running: {missing}", err=True)
        click.echo("Run:  docker compose up -d", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
