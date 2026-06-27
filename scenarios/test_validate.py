from dataclasses import dataclass

from scenarios.generate import GeneratedTx
from scenarios.validate import build_report


@dataclass
class Rec:
    txid: str
    wallet: str
    scenario: str


def test_per_wallet_recall_unique_and_misses():
    records = [
        Rec("t1", "Electrum", "default"),
        Rec("t2", "Electrum", "send_p2pkh"),
        Rec("t3", "Bitcoin Core", "default"),
    ]
    verdicts = {
        "t1": ({"Bitcoin Core", "Electrum"}, []),
        "t2": ({"Electrum"}, []),
        "t3": ({"Bitcoin Core", "Electrum"}, []),
    }
    report = build_report(records, lambda txid: verdicts[txid])
    assert report.total == 3
    assert report.per_wallet["Electrum"]["count"] == 2
    assert report.per_wallet["Electrum"]["recall"] == 1.0
    assert report.per_wallet["Electrum"]["unique"] == 0.5
    assert report.per_wallet["Bitcoin Core"]["recall"] == 1.0
    assert report.per_wallet["Bitcoin Core"]["unique"] == 0.0
    assert report.misses == []
    assert report.per_scenario["Electrum/send_p2pkh"]["recall"] == 1.0
    assert report.per_scenario["Electrum/send_p2pkh"]["count"] == 1


def test_per_scenario_aggregates_over_repeats():
    records = [
        Rec("a", "Electrum", "multi_output"),
        Rec("b", "Electrum", "multi_output"),
    ]
    verdicts = {"a": ({"Electrum"}, []), "b": ({"Bitcoin Core"}, [])}
    report = build_report(records, lambda txid: verdicts[txid])
    s = report.per_scenario["Electrum/multi_output"]
    assert s["count"] == 2
    assert s["recall"] == 0.5
    assert s["unique"] == 0.5


def test_miss_recorded_when_true_wallet_excluded():
    records = [Rec("t1", "Electrum", "multi_output")]
    report = build_report(records, lambda txid: ({"Bitcoin Core"}, []))
    assert report.per_wallet["Electrum"]["recall"] == 0.0
    assert report.misses == [{"txid": "t1", "wallet": "Electrum", "candidates": ["Bitcoin Core"]}]


def test_fingerprint_recall_counts_labeled_fingerprints_found():
    # labels and detector output share one vocabulary (the detector's strings).
    records = [
        GeneratedTx("a", "Electrum", "default", ["signals RBF", "BIP-69 followed by outputs"]),
        GeneratedTx("b", "Electrum", "send_p2tr", ["Sends to taproot address"]),
    ]
    # detector emits "signals RBF" (not BIP-69) for a, the taproot string for b
    # -> 2 of 3 labeled fingerprints found.
    verdicts = {
        "a": ({"Electrum"}, ["signals RBF"]),
        "b": ({"Electrum"}, ["Sends to taproot address"]),
    }
    report = build_report(records, lambda txid: verdicts[txid])
    assert report.fingerprint_recall == 2 / 3
