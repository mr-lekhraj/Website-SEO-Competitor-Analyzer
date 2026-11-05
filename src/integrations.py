import os

def load_gsc_rows(site_url):
    credential_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credential_path:
        return [], "GSC is not configured. Upload a CSV export or set GOOGLE_APPLICATION_CREDENTIALS."
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        credentials = service_account.Credentials.from_service_account_file(
            credential_path,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
        )
        service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
        # Sample date window: replace with a user-selected date range for production.
        result = service.searchanalytics().query(
            siteUrl=site_url,
            body={"startDate":"2026-10-01","endDate":"2026-10-31","dimensions":["query"],"rowLimit":100}
        ).execute()
        return result.get("rows", []), "Connected to Search Console. Showing the configured sample date window."
    except Exception as exc:
        return [], f"GSC connection failed: {exc}"

def ai_recommendations(site_url, audit, context=""):
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and audit:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            prompt = (
                f"Give five prioritized, evidence-based SEO actions for {site_url}. "
                f"Audit data: {audit}. Context: {context}. Do not invent traffic or rankings."
            )
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                messages=[{"role":"user","content":prompt}],
                temperature=0.2
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
        "Prioritize high-impression, low-CTR queries using Search Console page and query exports."
    ], "Showing rule-based recommendations. Configure OPENAI_API_KEY for generated recommendations."
