"""Electrum wallet creation and regtest configuration helpers."""

import contextlib
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


def electrum_python() -> str:
    # Electrum's deps live in its own venv beside run_electrum; the bare script's
    # shebang would fall back to system Python and miss them.
    override = os.getenv("ELECTRUM_PYTHON")
    if override:
        return override
    return str(Path(electrum_bin()).parent / "venv" / "bin" / "python")


def electrum_cmd() -> list[str]:
    return [electrum_python(), electrum_bin()]


def electrum_wallet_dir() -> Path:
    return Path.home() / ".electrum" / "regtest" / "wallets"


def wallet_path() -> Path:
    return electrum_wallet_dir() / WALLET_NAME


def _run_electrum(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        [*electrum_cmd(), "--regtest", *args],
        capture_output=True, text=True, timeout=timeout,
    )


def _daemon_alive() -> bool:
    # list_wallets only talks to the daemon process (no network), so it tells a
    # live daemon apart from a stale lockfile, which both make `daemon -d` say
    # "already running". The CLI exits 0 either way, so check the message.
    out = _run_electrum("list_wallets", timeout=10)
    return "daemon not running" not in (out.stdout + out.stderr).lower()


def _clear_daemon_lock() -> None:
    for name in ("daemon", "daemon_rpc_socket"):
        (electrum_config_dir() / name).unlink(missing_ok=True)


@contextlib.contextmanager
def electrum_daemon():
    """Run an Electrum regtest daemon for the duration of the block.

    Starts the daemon only if one is not already running, and stops only the
    daemon it started (so it never kills a GUI/daemon the user already has open).
    """
    result = _run_electrum("daemon", "-d")
    started = "starting daemon" in result.stdout.lower()
    if not started and not _daemon_alive():
        # An unclean shutdown leaves a lockfile that blocks startup forever;
        # clear it and retry rather than running every command daemon-less.
        _clear_daemon_lock()
        result = _run_electrum("daemon", "-d")
        started = "starting daemon" in result.stdout.lower()
    try:
        yield
    finally:
        if started:
            _run_electrum("stop")


def create_wallet_if_missing() -> None:
    """Create a standard Electrum regtest wallet non-interactively if absent."""
    wp = wallet_path()
    if wp.exists():
        return
    wp.parent.mkdir(parents=True, exist_ok=True)
    with electrum_daemon():
        created = _run_electrum("create", "-w", str(wp))
        if created.returncode != 0:
            raise RuntimeError(f"electrum create failed: {created.stderr}")
        loaded = _run_electrum("load_wallet", "-w", str(wp))
        if loaded.returncode != 0:
            raise RuntimeError(f"electrum load_wallet failed: {loaded.stderr}")


def get_wallet_address() -> str:
    """Return an unused receive address from the regtest wallet (via the daemon)."""
    wp = wallet_path()
    with electrum_daemon():
        _run_electrum("load_wallet", "-w", str(wp))
        result = _run_electrum("getunusedaddress", "-w", str(wp), timeout=15)
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

    existing = {}
    if config_file.exists():
        try:
            existing = json.loads(config_file.read_text())
        except (ValueError, OSError):
            existing = {}

    config = {
        # Without an up-to-date config_version Electrum runs a legacy migration
        # that rewrites the server's protocol to SSL; our Fulcrum speaks plain
        # TCP, so the daemon would then fail every connection. 3 is Electrum
        # 4.7.2's FINAL_CONFIG_VERSION.
        "config_version": 3,
        "auto_connect": False,
        "oneserver": True,
        "server": f"{fulcrum_host}:{fulcrum_port}:t",
    }
    # Preserve the daemon's RPC credentials. Overwriting the config without them
    # desyncs the CLI from an already-running daemon, which answers 403 Forbidden.
    for key in ("rpcuser", "rpcpassword", "rpcport", "rpchost", "rpcsock", "rpcsock_path"):
        if key in existing:
            config[key] = existing[key]

    config_file.write_text(json.dumps(config, indent=2))
