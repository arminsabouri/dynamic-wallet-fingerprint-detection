from scenarios.analyze import analyze_txids


def test_analyze_aggregates_wallets_and_fingerprints():
    verdicts = {
        "t1": ({"Electrum"}, ["bip69", "low_r"]),
        "t2": ({"Electrum", "Bitcoin Core"}, ["bip69"]),
        "t3": (set(), []),
    }
    report = analyze_txids(["t1", "t2", "t3"], lambda txid: verdicts[txid])
    assert report.total == 3
    assert report.wallet_counts == {"Electrum": 2, "Bitcoin Core": 1}
    assert report.fingerprint_counts == {"bip69": 2, "low_r": 1}
    assert report.per_tx["t1"] == {"wallets": ["Electrum"], "fingerprints": ["bip69", "low_r"]}
    assert report.per_tx["t3"] == {"wallets": [], "fingerprints": []}
