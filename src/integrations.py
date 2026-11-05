import os
from datetime import date, timedelta


def _setting(name, default=None):
    """Read Streamlit Cloud secrets first, then local environment variables."""
    try:
        import streamlit as st
        value = st.secrets.get(name, default)
        if value not in (None, ""):
            return value
    except Exception:
        pass
    return os.getenv(name, default)


def load_gsc_rows(site_url, start_date=None, end_date=None, property_id=None, row_limit=25000):
    credential_path = _setting("GOOGLE_APPLICATION_CREDENTIALS")
    service_account_info = _setting("gcp_service_account")
    if not credential_path and not service_account_info:
        return [], (
            "GSC is not configured. Upload a CSV export, set GOOGLE_APPLICATION_CREDENTIALS locally, "
            "or add a [gcp_service_account] object to Streamlit secrets."
        )
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
        if service_account_info:
            credentials = service_account.Credentials.from_service_account_info(dict(service_account_info), scopes=scopes)
        else:
            credentials = service_account.Credentials.from_service_account_file(credential_path, scopes=scopes)
        service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
        # GSC data may be delayed. Default to the previous 28-day window ending three days ago.
        end = end_date or (date.today() - timedelta(days=3))
        start = start_date or (end - timedelta(days=27))
        if start >= end:
            return [], "Start date must be earlier than end date."
        property_value = property_id or _setting("GSC_PROPERTY", site_url)
        result = service.searchanalytics().query(
            siteUrl=property_value,
            body={
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "dimensions": ["query", "page"],
                "rowLimit": min(max(int(row_limit), 1), 25000),
            },
        ).execute()
        return result.get("rows", []), f"Connected to Search Console property {property_value} for {start} through {end}."
    except Exception as exc:
        return [], f"GSC connection failed: {exc}"


def ai_recommendations(site_url, audit, context=""):
    api_key = _setting("OPENAI_API_KEY")
    model = _setting("OPENAI_MODEL", "gpt-4.1-mini")
    if api_key and audit:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            prompt = (
                f"Give five prioritized, evidence-based SEO actions for {site_url}. "
                f"Audit data: {audit}. Context: {context}. Do not invent traffic or rankings."
            )
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            items = [line.strip("- ").strip() for line in response.choices[0].message.content.splitlines() if line.strip()]
            return items, "Generated using the configured OpenAI API."
        except Exception as exc:
            return [f"AI provider error: {exc}"], "AI request failed."
    return [
        "Review pages with missing or overly short title tags and write unique, intent-aligned titles.",
        "Add useful meta descriptions to important landing pages; evaluate CTR changes in Search Console.",
        "Ensure each indexable page has one descriptive H1 and a logical heading structure.",
        "Add meaningful alt text to informative images; keep decorative images appropriately empty.",
        "Prioritize high-impression, low-CTR queries using Search Console page and query exports.",
    ], "Showing rule-based recommendations. Configure OPENAI_API_KEY for generated recommendations."
