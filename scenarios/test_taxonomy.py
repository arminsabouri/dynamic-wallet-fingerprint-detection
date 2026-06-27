from scenarios import taxonomy
from scenarios.scenarios import SCENARIOS
from scenarios.core_wallet import CORE_SCENARIOS


def test_tx_types_well_formed():
    assert taxonomy.TX_TYPES, "taxonomy must not be empty"
    for t in taxonomy.TX_TYPES:
        assert t.slug and isinstance(t.slug, str)
        assert t.description and isinstance(t.description, str)
    slugs = [t.slug for t in taxonomy.TX_TYPES]
    assert len(slugs) == len(set(slugs)), "slugs must be unique"


def test_every_scenario_slug_is_in_the_taxonomy():
    known = taxonomy.slugs()
    for sc in SCENARIOS:
        assert sc.label in known, f"Electrum scenario {sc.label} missing from taxonomy"
    for sc in CORE_SCENARIOS:
        assert sc.label in known, f"Core scenario {sc.label} missing from taxonomy"


def test_enumeration_checklist_lists_every_slug():
    text = taxonomy.enumeration_checklist()
    for t in taxonomy.TX_TYPES:
        assert t.slug in text
