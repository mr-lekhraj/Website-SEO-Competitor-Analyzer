from src.keywords import expand_keywords, infer_intent, cluster_keywords, detect_cannibalization


def test_calculator_expansion_uses_natural_phrases():
    rows = expand_keywords("molarity calculator")
    phrases = {row["keyword"] for row in rows}
    assert "molarity calculator" in phrases
    assert "how to calculate molarity" in phrases
    assert "molarity calculator online" in phrases
    assert "how to molarity calculator" not in phrases
    assert "calculator molarity calculator" not in phrases


def test_keyword_intent_rules():
    assert infer_intent("how to calculate molarity") == "Informational"
    assert infer_intent("best molarity calculator") == "Commercial"
    assert infer_intent("molarity calculator online") == "Transactional"


def test_multiple_seeds_are_deduplicated_and_clustered():
    rows = expand_keywords("molarity calculator\nmolarity calculator\nsample size calculator")
    assert len({row["keyword"] for row in rows}) == len(rows)
    assert {row["cluster"] for row in rows} == {"molarity calculator", "sample size calculator"}
    grouped = cluster_keywords(["molarity calculator", "molarity calculator online", "sample size calculator"])
    assert len(grouped) == 3
    assert grouped[0]["cluster_id"].startswith("C")


def test_detect_cannibalization_flags_same_query_across_two_pages():
    rows = [
        {"query": "molarity calculator", "page": "https://site.test/a", "clicks": 4, "impressions": 40},
        {"query": "molarity calculator", "page": "https://site.test/b", "clicks": 2, "impressions": 20},
        {"query": "sample size calculator", "page": "https://site.test/c", "clicks": 1, "impressions": 10},
    ]
    result = detect_cannibalization(rows)
    assert len(result) == 1
    assert result[0]["query"] == "molarity calculator"
    assert result[0]["page_count"] == 2
