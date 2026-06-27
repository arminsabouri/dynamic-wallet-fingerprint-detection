# scenarios/test_compare.py
from scenarios import compare


def test_vocabulary_is_detector_strings_and_excludes_intent_only():
    vocab = compare.electrum_fingerprint_vocabulary()
    # detectable baseline fingerprints, in the detector's own wording
    assert "Sends to taproot address" in vocab   # output_p2tr
    assert "signals RBF" in vocab                 # rbf
    # our raw slugs and intent-only labels are NOT in the vocabulary
    assert "output_p2tr" not in vocab
    assert "coin_control" not in vocab
    assert "manual_feerate" not in vocab


def test_coverage_splits_covered_and_missing():
    vocab = compare.electrum_fingerprint_vocabulary()
    # agent produced exactly one known detector fingerprint plus an unrelated one
    agent = {"Sends to taproot address", "something_else"}
    report = compare.coverage(agent)
    assert "Sends to taproot address" in report.covered
    assert "Sends to taproot address" not in report.missing
    assert report.missing == vocab - {"Sends to taproot address"}
    assert report.rate == len(report.covered) / len(vocab)


def test_full_coverage_rate_is_one():
    vocab = compare.electrum_fingerprint_vocabulary()
    report = compare.coverage(set(vocab))
    assert report.rate == 1.0
    assert report.missing == set()
