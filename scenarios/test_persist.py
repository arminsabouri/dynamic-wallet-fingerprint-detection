import json
from dataclasses import dataclass

from scenarios.persist import save_dataset
from scenarios.validate import Report


@dataclass
class Rec:
    txid: str
    wallet: str
    scenario: str
    fingerprints: list


def test_save_dataset_writes_json(tmp_path):
    records = [Rec("t1", "Electrum", "default", ["bip69"])]
    report = Report(total=1, per_wallet={"Electrum": {"count": 1, "recall": 1.0, "unique": 1.0}},
                    per_scenario={"Electrum/default": {"candidates": ["Electrum"], "recall": True}},
                    misses=[])
    save_dataset(records, report, tmp_path)

    dataset = json.loads((tmp_path / "dataset.json").read_text())
    assert dataset[0] == {"txid": "t1", "wallet": "Electrum", "scenario": "default", "fingerprints": ["bip69"]}
    saved_report = json.loads((tmp_path / "report.json").read_text())
    assert saved_report["per_wallet"]["Electrum"]["recall"] == 1.0
    assert saved_report["total"] == 1
