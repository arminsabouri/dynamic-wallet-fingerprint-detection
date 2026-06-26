from dataclasses import dataclass


@dataclass
class AnalysisReport:
    total: int
    per_tx: dict            # txid -> {"wallets": [...], "fingerprints": [...]}
    wallet_counts: dict     # wallet -> number of txs it was a candidate for
    fingerprint_counts: dict  # fingerprint -> number of txs exhibiting it


def analyze_txids(txids, detect_fn) -> AnalysisReport:
    """Run the detector over unlabeled txids and aggregate what it found.

    Unlike build_report, there is no ground truth here: this is for txs of
    unknown provenance (e.g. produced by the GUI agent), so it reports what
    the detector says rather than scoring recall.
    """
    per_tx = {}
    wallet_counts = {}
    fingerprint_counts = {}
    for txid in txids:
        wallets, fingerprints = detect_fn(txid)
        per_tx[txid] = {"wallets": sorted(wallets), "fingerprints": sorted(fingerprints)}
        for w in wallets:
            wallet_counts[w] = wallet_counts.get(w, 0) + 1
        for f in fingerprints:
            fingerprint_counts[f] = fingerprint_counts.get(f, 0) + 1
    return AnalysisReport(
        total=len(per_tx),
        per_tx=per_tx,
        wallet_counts=wallet_counts,
        fingerprint_counts=fingerprint_counts,
    )
