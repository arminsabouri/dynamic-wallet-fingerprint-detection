"""Launch and terminate the Electrum Qt process."""

import os
import signal
import subprocess
import time

from wallets.electrum.setup import electrum_cmd, wallet_path, _run_electrum, _daemon_alive

_proc: subprocess.Popen | None = None


def _ensure_no_daemon(timeout: float = 12.0) -> None:
    """Stop any daemon and wait for it to exit before launching the GUI.

    `electrum stop` returns before the process dies, which otherwise races the GUI launch.
    """
    _run_electrum("stop")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _daemon_alive():
            return
        time.sleep(0.5)


def start() -> None:
    """Launch Electrum GUI. Blocks ~3s for the window to appear."""
    global _proc
    _ensure_no_daemon()
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
