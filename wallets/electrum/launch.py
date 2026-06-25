"""Launch and terminate the Electrum Qt process."""

import os
import signal
import subprocess
import time

from wallets.electrum.setup import electrum_cmd, wallet_path

_proc: subprocess.Popen | None = None


def start() -> None:
    """Launch Electrum GUI. Blocks ~3s for the window to appear."""
    global _proc
    wp = str(wallet_path())
    _proc = subprocess.Popen(
        [*electrum_cmd(), "--regtest", "--wallet", wp, "--gui", "qt"],
        env=os.environ.copy(),
    )
    time.sleep(4.0)  # give Qt time to render the main window


def stop() -> None:
    global _proc
    if _proc and _proc.poll() is None:
        _proc.send_signal(signal.SIGTERM)
        try:
            _proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            _proc.kill()
    _proc = None


def is_running() -> bool:
    return _proc is not None and _proc.poll() is None
