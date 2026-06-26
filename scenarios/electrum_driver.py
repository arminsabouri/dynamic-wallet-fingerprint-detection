import json
import os
import subprocess
import time
from pathlib import Path


def _base_cmd() -> list[str]:
    py = os.getenv("ELECTRUM_PYTHON", str(Path.home() / "electrum" / "venv" / "bin" / "python"))
    binp = os.getenv("ELECTRUM_BIN", str(Path.home() / "electrum" / "run_electrum"))
    return [py, binp, "--regtest"]


def _wallet() -> str:
    return os.getenv(
        "ELECTRUM_WALLET",
        str(Path.home() / ".electrum" / "regtest" / "wallets" / "default_wallet"),
    )


def _run(args: list[str], *, with_wallet: bool = True, timeout: int = 60) -> str:
    cmd = [*_base_cmd(), *args]
    if with_wallet:
        cmd += ["-w", _wallet()]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"electrum {args[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def payto(destination: str, amount, *, rbf=None, feerate=None, locktime=None, from_coins=None) -> str:
    args = ["payto", destination, str(amount)]
    if rbf is not None:
        args += ["--rbf", "true" if rbf else "false"]
    if feerate is not None:
        args += ["--feerate", str(feerate)]
    if locktime is not None:
        args += ["--locktime", str(locktime)]
    if from_coins is not None:
        args += ["--from_coins", json.dumps(from_coins)]
    return _run(args)


def paytomany(outputs, *, rbf=None, feerate=None, from_coins=None) -> str:
    outs = json.dumps([[addr, str(amount)] for addr, amount in outputs])
    args = ["paytomany", outs]
    if rbf is not None:
        args += ["--rbf", "true" if rbf else "false"]
    if feerate is not None:
        args += ["--feerate", str(feerate)]
    if from_coins is not None:
        args += ["--from_coins", json.dumps(from_coins)]
    return _run(args)


def listunspent() -> list:
    return json.loads(_run(["listunspent"]))


def wait_for_coins(*, min_count: int = 1, attempts: int = 40, poll: float = 0.5) -> list:
    """Block until the wallet shows at least `min_count` spendable coins.

    Electrum trails the chain while Fulcrum indexes a freshly mined block, so
    coin selection can briefly see an empty wallet and a payto fail. Polling
    here instead of a fixed sleep keeps generation reliable without overwaiting.
    """
    coins = []
    for _ in range(attempts):
        coins = listunspent()
        if len(coins) >= min_count:
            return coins
        time.sleep(poll)
    return coins


def broadcast(tx_hex: str) -> str:
    return _run(["broadcast", tx_hex], with_wallet=False)
