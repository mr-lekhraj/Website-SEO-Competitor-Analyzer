"""Google Search Console CSV normalization helpers."""
from __future__ import annotations
import re
from io import BytesIO, StringIO
import pandas as pd

ALIASES = {
    "query": {"query", "queries", "top queries", "search query"},
    "page": {"page", "pages", "top pages", "landing page", "url", "top url"},
    "clicks": {"clicks", "click"},
    "impressions": {"impressions", "impression"},
    "ctr": {"ctr", "click through rate", "click-through rate"},
    "position": {"position", "average position", "avg position"},
}


def _header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).replace("\ufeff", "").lower()).strip()


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False).str.strip(),
        errors="coerce",
    )


def parse_gsc_csv(file_obj) -> pd.DataFrame:
    """Normalize standard GSC Queries and query+page CSV exports."""
    if hasattr(file_obj, "read"):
        raw = file_obj.read()
        frame = pd.read_csv(StringIO(raw)) if isinstance(raw, str) else pd.read_csv(BytesIO(raw))
    else:
        frame = pd.read_csv(file_obj, encoding="utf-8-sig")
    if frame.empty:
        raise ValueError("The uploaded CSV contains no data rows.")
    rename = {}
    for column in frame.columns:
        key = _header_key(column)
        for canonical, aliases in ALIASES.items():
            if key in aliases:
                rename[column] = canonical
                break
    frame = frame.rename(columns=rename)
    if "query" not in frame.columns:
        raise ValueError("Could not find a Search Console query column. Expected 'Top queries', 'Queries' or 'Query'.")
    for column in ("page", "clicks", "impressions", "ctr", "position"):
        if column not in frame.columns:
            frame[column] = None
    frame["query"] = frame["query"].fillna("").astype(str).str.strip()
    frame["page"] = frame["page"].fillna("").astype(str).str.strip()
    frame = frame[frame["query"] != ""].copy()
    for column in ("clicks", "impressions", "ctr", "position"):
        frame[column] = _numeric(frame[column])
    if frame["ctr"].dropna().gt(1).any():
        frame["ctr"] = frame["ctr"] / 100.0
    if frame.empty:
        raise ValueError("No valid search queries were found in the CSV.")
    result = frame.groupby(["query", "page"], dropna=False, as_index=False).agg(
        clicks=("clicks", "sum"),
        impressions=("impressions", "sum"),
        position=("position", "mean"),
        ctr=("ctr", "mean"),
    )
    valid = result["impressions"].fillna(0) > 0
    result.loc[valid, "ctr"] = result.loc[valid, "clicks"] / result.loc[valid, "impressions"]
    return result[["query", "page", "clicks", "impressions", "ctr", "position"]].sort_values(
        ["impressions", "clicks"], ascending=False, na_position="last"
    ).reset_index(drop=True)


def gsc_api_rows_to_frame(rows: list[dict]) -> pd.DataFrame:
    normalized = []
    for row in rows:
        keys = row.get("keys", [])
        normalized.append({
            "query": keys[0] if len(keys) > 0 else "",
            "page": keys[1] if len(keys) > 1 else "",
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": row.get("ctr", 0),
            "position": row.get("position"),
        })
    return pd.DataFrame(normalized, columns=["query", "page", "clicks", "impressions", "ctr", "position"])
