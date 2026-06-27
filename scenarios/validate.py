from dataclasses import dataclass


@dataclass
class Report:
    total: int
    per_wallet: dict   # wallet -> {"count": int, "recall": float, "unique": float}
    per_scenario: dict # "wallet/scenario" -> {"candidates": [...], "recall": bool}
    misses: list       # [{"txid","wallet","candidates"}]
    fingerprint_recall: float = 0.0


def build_report(records, detect_fn) -> Report:
    rows = [(rec, *detect_fn(rec.txid)) for rec in records]
    agg = {}
    sc_agg = {}
    misses = []
    for rec, candidates, fps in rows:
        w = rec.wallet
        a = agg.setdefault(w, {"count": 0, "in": 0, "unique": 0})
        a["count"] += 1
        if w in candidates:
            a["in"] += 1
        else:
            misses.append({"txid": rec.txid, "wallet": w, "candidates": sorted(candidates)})
        if candidates == {w}:
            a["unique"] += 1

        s = sc_agg.setdefault(f"{w}/{rec.scenario}", {"count": 0, "in": 0, "unique": 0})
        s["count"] += 1
        if w in candidates:
            s["in"] += 1
        if candidates == {w}:
            s["unique"] += 1

    per_wallet = {
        w: {"count": a["count"], "recall": a["in"] / a["count"], "unique": a["unique"] / a["count"]}
        for w, a in agg.items()
    }
    per_scenario = {
        k: {"count": s["count"], "recall": s["in"] / s["count"], "unique": s["unique"] / s["count"]}
        for k, s in sc_agg.items()
    }

    # Fingerprint-recall: of the labeled fingerprints, how many the detector emitted
    # (both sides use the detector's vocabulary, so a direct membership check).
    labeled = 0
    found = 0
    for rec, _candidates, fps in rows:
        detected = set(fps)
        for fp in getattr(rec, "fingerprints", []):
            labeled += 1
            if fp in detected:
                found += 1
    fingerprint_recall = (found / labeled) if labeled else 0.0

    return Report(
        total=len(rows),
        per_wallet=per_wallet,
        per_scenario=per_scenario,
        misses=misses,
        fingerprint_recall=fingerprint_recall,
    )
