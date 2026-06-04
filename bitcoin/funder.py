"""Ensure the wallet under test has enough funded UTXOs before each scenario."""

import time

from bitcoin.regtest import RegtestNode


def fund_wallet(
    node: RegtestNode,
    receive_address: str,
    amount_btc: float = 1.0,
    utxo_count: int = 5,
    confirm: bool = True,
) -> list[str]:
    """Send `utxo_count` UTXOs of `amount_btc` each to `receive_address`.

    Returns list of txids. Mines 1 block to confirm if `confirm=True`.
    """
    txids = []
    for _ in range(utxo_count):
        txid = node.fund_address(receive_address, amount_btc)
        txids.append(txid)
        time.sleep(0.1)

    if confirm:
        node.mine_blocks(1)
        time.sleep(1.0)  # let Fulcrum index the block

    return txids


def reset_wallet_utxos(
    node: RegtestNode,
    receive_address: str,
    amount_btc: float = 1.0,
    utxo_count: int = 5,
) -> list[str]:
    """Mine a fresh batch of UTXOs. Used between scenarios to get clean state."""
    node.ensure_mature_coins()
    return fund_wallet(node, receive_address, amount_btc, utxo_count, confirm=True)
