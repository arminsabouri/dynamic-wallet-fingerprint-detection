import json
import os
import subprocess
from pathlib import Path

_REGTEST_INI = (
    "[RPC_INFO]\n"
    "URL = http://127.0.0.1:18443\n"
    "RPCUSER = bitcoin\n"
    "RPCPASSWORD = bitcoin\n"
)

# Runs in Ishaana's repo; prints one JSON line with the result.
_DETECT_SCRIPT = """
import json, sys
from bitcoin_core import BitcoinCore
from fingerprinting import detect_wallet
tx = BitcoinCore().get_tx(sys.argv[1])
wallets, fingerprints = detect_wallet(tx)
print(json.dumps([[getattr(w, "value", str(w)) for w in wallets], list(fingerprints)]))
"""


def _repo() -> str:
    return os.getenv("ISHAANA_REPO", str(Path.home() / "wallet-fingerprinting"))


def _ensure_config(repo: str) -> None:
    # The repo ships a mainnet config, so always overwrite it for regtest.
    (Path(repo) / "rpc_config.ini").write_text(_REGTEST_INI)


def _python() -> str:
    # Ishaana's deps live in her own interpreter, not this project's uv env.
    override = os.getenv("ISHAANA_PYTHON")
    if override:
        return override
    venv_py = Path(_repo()) / "venv" / "bin" / "python"
    return str(venv_py) if venv_py.exists() else "python3"


def detect(txid: str) -> tuple[set[str], list[str]]:
    """Run Ishaana's detect_wallet on a regtest txid via a subprocess.

    Returns (wallet_names, fingerprints_found).
    """
    repo = _repo()
    _ensure_config(repo)
    result = subprocess.run(
        [_python(), "-c", _DETECT_SCRIPT, txid],
        cwd=repo,  # her bitcoin_core.py reads rpc_config.ini relative to CWD
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"detector failed for {txid}: {result.stderr.strip()[-500:]}")
    wallets, fingerprints = json.loads(result.stdout.strip().splitlines()[-1])
    return set(wallets), list(fingerprints)
