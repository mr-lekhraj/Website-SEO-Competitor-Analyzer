from datetime import date

def build_report(name, url, keywords, audit):
    lines = [
        f"# SEO Report — {name}",
        f"**Website:** {url}",
        f"**Generated:** {date.today().isoformat()}",
        "",
        "## Executive summary",
        f"- Keyword ideas tracked: {len(keywords)}",
        f"- Latest technical audit score: {audit['score']}/100" if audit else "- Technical audit: not yet run",
        "",
        "## Keyword ideas"
    ]
    lines.extend(f"- {row['keyword']} — {row['intent']} ({row['source']})" for row in keywords[:150])
    if audit:
        lines.extend(["", "## Technical audit"])
        lines.extend(f"- **{row['status']}** — {row['check']}: {row['details']}" for row in audit.get("checks", []))
    lines.extend([
        "", "## Data limitations",
        "Search volume, keyword difficulty, live rankings and backlink metrics require a connected data provider or imported exports. This report does not fabricate those metrics."
    ])
    return "\n".join(lines)
