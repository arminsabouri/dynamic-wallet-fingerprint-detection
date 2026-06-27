"""Single source of truth for the transaction types.

The Electrum baseline, the Core contrast generator, and the agent's enumeration
prompt all draw from this list. Expected fingerprints stay per-backend.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TxType:
    slug: str
    description: str


TX_TYPES = [
    TxType("default", "A standard send with wallet defaults: single recipient, change output, RBF enabled."),
    TxType("send_p2pkh", "Send to a legacy P2PKH (1...) address."),
    TxType("send_p2wpkh", "Send to a native segwit P2WPKH (bc1q...) address."),
    TxType("send_p2tr", "Send to a taproot P2TR (bc1p...) address."),
    TxType("no_rbf", "Send with RBF disabled (final nSequence)."),
    TxType("manual_feerate", "Send with a user-specified fee rate (sat/vbyte)."),
    TxType("multi_output", "Batch payment to multiple recipients in one transaction."),
    TxType("coin_control", "Manually select which UTXO funds the send."),
    TxType("changeless", "Send-max so the transaction has no change output."),
]

BY_SLUG = {t.slug: t for t in TX_TYPES}


def slugs() -> set[str]:
    return set(BY_SLUG)


def enumeration_checklist() -> str:
    """Render the vocabulary as a bullet list for the agent's system prompt."""
    return "\n".join(f"- {t.slug}: {t.description}" for t in TX_TYPES)
