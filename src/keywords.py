MODIFIERS = {
    "Informational": ["what is", "how to", "guide", "examples", "explained", "tutorial"],
    "Commercial": ["best", "top", "comparison", "review", "alternatives"],
    "Transactional": ["free download", "online", "tool", "calculator", "template"],
}

def expand_keywords(seed_text):
    seeds = [item.strip() for item in seed_text.replace(",", "\n").splitlines() if item.strip()]
    results = {}
    for seed in seeds:
        base = seed.lower()
        results[base] = {"keyword": base, "intent": "Mixed", "source": "Seed keyword"}
        for intent, modifiers in MODIFIERS.items():
            for modifier in modifiers:
                phrase = f"{modifier} {base}".lower()
                results[phrase] = {"keyword": phrase, "intent": intent, "source": "Modifier expansion"}
    return list(results.values())
