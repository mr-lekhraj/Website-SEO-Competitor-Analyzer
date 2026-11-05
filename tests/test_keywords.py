from src.keywords import expand_keywords

def test_expansion_includes_seed_and_intent_variants():
    rows = expand_keywords("molarity calculator")
    assert any(row["keyword"] == "molarity calculator" for row in rows)
    assert any(row["intent"] == "Informational" for row in rows)
