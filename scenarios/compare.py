"""Coverage of the deterministic baseline's fingerprints by the GUI agent.

Scenarios carry the detector's exact strings, so this is a direct intersection.
"""
from dataclasses import dataclass

from scenarios.scenarios import SCENARIOS


def electrum_fingerprint_vocabulary() -> set[str]:
    return {fp for sc in SCENARIOS for fp in sc.fingerprints}


@dataclass
class CoverageReport:
    covered: set[str]
    missing: set[str]
    rate: float


def coverage(agent_fingerprints: set[str]) -> CoverageReport:
    vocab = electrum_fingerprint_vocabulary()
    covered = vocab & set(agent_fingerprints)
    missing = vocab - covered
    rate = (len(covered) / len(vocab)) if vocab else 0.0
    return CoverageReport(covered=covered, missing=missing, rate=rate)
