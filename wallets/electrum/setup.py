"""Electrum wallet creation and regtest configuration helpers."""

import os
import subprocess
import time
from pathlib import Path

WALLET_NAME = "dwf_regtest"


def electrum_bin() -> str:
    # setup.py lives at <repo>/wallets/electrum/, so parents[2] is the repo root
    repo_root = Path(__file__).resolve().parents[2]
    default = repo_root.parent / "electrum" / "run_electrum"
    return os.getenv("ELECTRUM_BIN", str(default))


def electrum_wallet_dir() -> Path:
    return Path.home() / ".electrum" / "regtest" / "wallets"


def wallet_path() -> Path:
    return electrum_wallet_dir() / WALLET_NAME


def create_wallet_if_missing() -> None:
    """Create a standard Electrum regtest wallet non-interactively if absent."""
    wp = wallet_path()
    if wp.exists():
        return

    wp.parent.mkdir(parents=True, exist_ok=True)
    bin = electrum_bin()

    # Create a new seed
    seed_result = subprocess.run(
        [bin, "--regtest", "createseed"],
        capture_output=True, text=True, timeout=30,
    )
    seed = seed_result.stdout.strip().strip('"')
    if not seed:
        raise RuntimeError(f"electrum createseed failed: {seed_result.stderr}")

    # Restore the wallet from seed (creates the wallet file)
    restore_result = subprocess.run(
        [bin, "--regtest", "restore", seed, "--wallet", str(wp)],
        capture_output=True, text=True, timeout=30,
    )
    if restore_result.returncode != 0:
        raise RuntimeError(f"electrum restore failed: {restore_result.stderr}")


def get_wallet_address() -> str:
    """Return an unused receive address from the regtest wallet (via CLI)."""
    bin = electrum_bin()
    wp = wallet_path()
    result = subprocess.run(
        [bin, "--regtest", "getunusedaddress", "--wallet", str(wp)],
        capture_output=True, text=True, timeout=15,
    )
    addr = result.stdout.strip().strip('"')
    if not addr:
        raise RuntimeError(f"Could not get address: {result.stderr}")
    return addr


def electrum_config_dir() -> Path:
    return Path.home() / ".electrum" / "regtest"


def write_electrum_config(fulcrum_host: str = "127.0.0.1", fulcrum_port: int = 50001) -> None:
    """Write Electrum's config file to point at local Fulcrum for regtest."""
    import json
    config_dir = electrum_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config"

    config = {
        "auto_connect": False,
        "oneserver": True,
        "server": f"{fulcrum_host}:{fulcrum_port}:t",
        "network": "regtest",
    }
    config_file.write_text(json.dumps(config, indent=2))
