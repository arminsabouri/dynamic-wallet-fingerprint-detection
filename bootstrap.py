"""Shared regtest wallet setup for the agent entrypoints (run.py, smoke_agent.py)."""
import time

from wallets.electrum import setup as esetup


def prepare_wallet(node, *, coins: float, fulcrum_host: str = "127.0.0.1", fulcrum_port: int = 50001) -> str:
    """Configure Electrum, create + fund the wallet, return its address.

    The caller owns the node lifecycle and the GUI launch.
    """
    esetup.write_electrum_config(fulcrum_host, fulcrum_port)
    esetup.create_wallet_if_missing()
    addr = esetup.get_wallet_address()
    node.fund_address(addr, coins)
    node.mine_blocks(1)
    time.sleep(3.0)  # Fulcrum indexing
    return addr
