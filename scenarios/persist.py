import json
from dataclasses import asdict, is_dataclass
from pathlib import Path


def save_dataset(records, report, out_dir) -> None:
    """Write dataset.json (labeled records) and report.json (aggregated report)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    dataset = [
        {
            "txid": r.txid,
            "wallet": r.wallet,
            "scenario": r.scenario,
            "fingerprints": list(r.fingerprints),
        }
        for r in records
    ]
    (out / "dataset.json").write_text(json.dumps(dataset, indent=2))

    report_obj = asdict(report) if is_dataclass(report) else report
    (out / "report.json").write_text(json.dumps(report_obj, indent=2))
