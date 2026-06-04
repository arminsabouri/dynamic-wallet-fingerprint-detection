"""Launch and terminate the Electrum Qt process."""

import os
import signal
import subprocess
import time

from wallets.electrum.setup import electrum_bin, wallet_path

_proc: subprocess.Popen | None = None


def start() -> None:
    """Launch Electrum GUI. Blocks ~3s for the window to appear."""
    global _proc
    bin_ = electrum_bin()
    wp = str(wallet_path())
    _proc = subprocess.Popen(
        [bin_, "--regtest", "--wallet", wp, "--gui", "qt"],
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
