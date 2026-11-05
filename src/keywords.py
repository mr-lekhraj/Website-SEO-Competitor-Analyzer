"""Keyword discovery, intent classification, clustering and opportunity helpers.

Generated ideas are heuristics. No search volume, keyword difficulty, CPC or rankings
are estimated without a verified data provider.
"""
from __future__ import annotations
import re
import unicodedata
from collections import defaultdict

INFO_MARKERS = (
    "what is", "how to", "how does", "formula", "definition", "meaning",
    "examples", "explained", "guide", "tutorial", "steps", "vs ", "difference between",
)
COMMERCIAL_MARKERS = ("best ", "top ", "review", "reviews", "comparison", "compare", "alternative", "alternatives")
TRANSACTIONAL_MARKERS = ("online", "free", "download", "use online", "tool", "calculator", "template", "generator")
STOP_WORDS = {"a", "an", "and", "for", "in", "of", "on", "the", "to", "with", "by"}


def normalize_keyword(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip().lower()


def tokenize(value: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", normalize_keyword(value))
    return {word for word in words if word not in STOP_WORDS and len(word) > 1}


def infer_intent(keyword: str) -> str:
    phrase = f" {normalize_keyword(keyword)} "
    if any(marker in phrase for marker in COMMERCIAL_MARKERS):
        return "Commercial"
    if any(marker in phrase for marker in INFO_MARKERS):
        return "Informational"
    if any(marker in phrase for marker in TRANSACTIONAL_MARKERS):
        return "Transactional"
    return "Mixed"


def _concept(seed: str) -> str:
    concept = re.sub(r"\b(calculator|tool|online|generator|builder|software|template)s?\b", " ", seed)
    concept = re.sub(r"\s+", " ", concept).strip()
    return concept or seed


def _candidate_phrases(seed: str) -> list[str]:
    base = normalize_keyword(seed)
    concept = _concept(base)
    candidates = [base]
    if "calculator" in base:
        candidates.extend([
            f"{concept} calculator online",
            f"free {concept} calculator",
            f"{concept} calculator with steps",
            f"{concept} calculator with formula",
            f"how to calculate {concept}",
            f"{concept} formula",
            f"{concept} calculation examples",
            f"{concept} calculation steps",
        ])
    elif "generator" in base:
        candidates.extend([
            f"{concept} generator online", f"free {concept} generator",
            f"how to use {concept} generator", f"{concept} examples", f"{concept} format",
        ])
    elif "builder" in base:
        candidates.extend([
            f"{concept} builder online", f"free {concept} builder",
            f"how to create {concept}", f"{concept} examples", f"{concept} template",
        ])
    else:
        candidates.extend([
            f"what is {base}", f"how to use {base}", f"{base} guide",
            f"{base} examples", f"{base} template",
        ])
    candidates.extend([f"best {base}", f"{base} alternatives", f"{base} comparison"])
    cleaned = []
    for candidate in candidates:
        candidate = normalize_keyword(candidate)
        if not candidate or candidate in cleaned:
            continue
        if re.search(r"\b(\w+)\s+\1\b", candidate):
            continue
        cleaned.append(candidate)
    return cleaned


def expand_keywords(seed_text: str, target_url: str = "") -> list[dict]:
    seeds = [normalize_keyword(x) for x in re.split(r"[,\n\r]+", seed_text or "")]
    seeds = list(dict.fromkeys(x for x in seeds if x))
    results: dict[str, dict] = {}
    for seed in seeds:
        for phrase in _candidate_phrases(seed):
            is_seed = phrase == seed
            results.setdefault(phrase, {
                "keyword": phrase,
                "intent": "Mixed" if is_seed else infer_intent(phrase),
                "source": "Seed keyword" if is_seed else "Natural variation",
                "cluster": seed,
                "target_url": target_url.strip(),
                "search_volume": None,
                "keyword_difficulty": None,
                "cpc": None,
            })
    return sorted(results.values(), key=lambda row: (row["cluster"], row["source"] != "Seed keyword", row["keyword"]))


def cluster_keywords(keywords: list[str], similarity_threshold: float = 0.5) -> list[dict]:
    normalized = list(dict.fromkeys(normalize_keyword(x) for x in keywords if normalize_keyword(x)))
    clusters: list[dict] = []
    for phrase in normalized:
        terms = tokenize(phrase)
        best_index, best_score = None, 0.0
        for index, cluster in enumerate(clusters):
            union = terms | cluster["terms"]
            score = len(terms & cluster["terms"]) / len(union) if union else 0.0
            if score > best_score:
                best_index, best_score = index, score
        if best_index is not None and best_score >= similarity_threshold:
            clusters[best_index]["keywords"].append(phrase)
            clusters[best_index]["terms"].update(terms)
        else:
            clusters.append({"label": phrase, "keywords": [phrase], "terms": set(terms)})
    output = []
    for index, cluster in enumerate(clusters, start=1):
        output.extend(
            {"keyword": phrase, "cluster": cluster["label"], "cluster_id": f"C{index:03d}"}
            for phrase in cluster["keywords"]
        )
    return output


def detect_cannibalization(rows: list[dict], min_impressions: int = 1) -> list[dict]:
    grouped = defaultdict(lambda: {"pages": set(), "clicks": 0.0, "impressions": 0.0})
    for row in rows:
        query = normalize_keyword(row.get("query") or row.get("keyword") or "")
        page = str(row.get("page") or row.get("url") or "").strip()
        if not query or not page:
            continue
        item = grouped[query]
        item["pages"].add(page)
        item["clicks"] += float(row.get("clicks") or 0)
        item["impressions"] += float(row.get("impressions") or 0)
    findings = []
    for query, item in grouped.items():
        if len(item["pages"]) >= 2 and item["impressions"] >= min_impressions:
            findings.append({
                "query": query, "pages": sorted(item["pages"]),
                "page_count": len(item["pages"]), "clicks": round(item["clicks"], 2),
                "impressions": round(item["impressions"], 2),
                "review_note": "Review page intent and internal linking; multiple ranking URLs are not automatically a problem.",
            })
    return sorted(findings, key=lambda item: (-item["impressions"], item["query"]))
