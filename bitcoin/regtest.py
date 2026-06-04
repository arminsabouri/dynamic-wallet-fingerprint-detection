"""Bitcoin Core regtest RPC wrapper."""

import os
import time
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException


def _rpc_url() -> str:
    user = os.getenv("BITCOIN_RPC_USER", "bitcoin")
    pw = os.getenv("BITCOIN_RPC_PASS", "bitcoin")
    host = os.getenv("BITCOIN_RPC_HOST", "127.0.0.1")
    port = os.getenv("BITCOIN_RPC_PORT", "18443")
    return f"http://{user}:{pw}@{host}:{port}"


class RegtestNode:
    """Thin wrapper around Bitcoin Core's regtest RPC."""

    def __init__(self, wallet_name: str = "") -> None:
        base = _rpc_url()
        self._base_url = base
        self._wallet_name = wallet_name
        self._rpc = self._connect(wallet_name)

    def _connect(self, wallet_name: str = "") -> AuthServiceProxy:
        url = self._base_url
        if wallet_name:
            url = f"{url}/wallet/{wallet_name}"
        return AuthServiceProxy(url)

    # -- Wallet management --

    def create_or_load_wallet(self, name: str, descriptors: bool = True) -> None:
        existing = self._rpc.listwallets()
        if name in existing:
            return
        try:
            self._rpc.loadwallet(name)
        except JSONRPCException:
            self._rpc.createwallet(name, False, False, "", False, descriptors)
        self._wallet_name = name
        self._rpc = self._connect(name)

    def get_new_address(self, label: str = "", addr_type: str = "bech32") -> str:
        return self._rpc.getnewaddress(label, addr_type)

    # -- Funding --

    def mine_blocks(self, count: int = 1, address: str | None = None) -> list[str]:
        if address is None:
            address = self.get_new_address()
        return self._rpc.generatetoaddress(count, address)

    def fund_address(self, address: str, amount_btc: float) -> str:
        txid = self._rpc.sendtoaddress(address, amount_btc)
        return txid

    def ensure_mature_coins(self) -> None:
        """Mine enough blocks so coinbase outputs are spendable (101 blocks)."""
        info = self._rpc.getblockchaininfo()
        height = info["blocks"]
        if height < 101:
            self.mine_blocks(101 - height + 1)

    # -- Transaction fetching --

    def get_raw_transaction(self, txid: str) -> dict:
        return self._rpc.getrawtransaction(txid, True)

    def get_raw_hex(self, txid: str) -> str:
        return self._rpc.getrawtransaction(txid, False)

    def get_block_count(self) -> int:
        return self._rpc.getblockcount()

    def wait_for_tx_in_mempool(self, txid: str, timeout: float = 30.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                mempool = self._rpc.getrawmempool()
                if txid in mempool:
                    return
            except JSONRPCException:
                pass
            time.sleep(1.0)
        raise TimeoutError(f"Transaction {txid} not in mempool after {timeout}s")

    def confirm_tx(self, txid: str) -> str:
        """Mine 1 block and verify txid is confirmed. Returns block hash."""
        self.wait_for_tx_in_mempool(txid)
        blocks = self.mine_blocks(1)
        return blocks[0]

    # -- Raw RPC passthrough --

    def rpc(self) -> AuthServiceProxy:
        return self._rpc
