# Website SEO Competitor Analyzer

A multi-website SEO research workspace built with Python and Streamlit.

## Keyword Research Engine v2.0
- Natural phrase patterns for calculator, generator, builder and general research seeds
- Rule-based search-intent labels (Informational, Commercial, Transactional, Mixed)
- Seed-based keyword clustering
- Editable keyword-to-landing-page mapping
- Search Console CSV normalization for common Query / Top queries and optional Page exports
- Query + page cannibalization review flags based on Search Console data
- Persistent GSC query/page imports with clicks, impressions, CTR, position, source and import history
- CSV exports for keyword inventory and normalized GSC data

The keyword generator produces ideas, not validated demand estimates. Search volume, keyword difficulty and CPC remain blank until connected to a real keyword-data provider. GSC performance metrics are sourced only from uploaded exports or an authorized Search Console connection.

## Other modules
- Multi-website project workspace backed by SQLite
- Competitor page metadata comparison
- Content-gap comparison from supplied topic / URL lists
- Technical/on-page audit: HTTP status, HTTPS, title, meta description, H1, canonical, robots meta, image alt, internal links and viewport
- Backlink and rank-tracking CSV preview foundations
- Optional AI recommendations through OpenAI API
- Markdown report export
- GitHub Actions tests

## Quick start
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud
1. Open https://share.streamlit.io/ and sign in with GitHub.
2. Create an app from `mr-lekhraj/Website-SEO-Competitor-Analyzer`, branch `main`, entrypoint `app.py`.
3. Configure optional API credentials in the app's Settings → Secrets. Never commit keys.
4. This starter has no user authentication and SQLite data is shared by viewers of the same deployment. Keep the deployed app private and do not enter sensitive client data.

## Google Search Console
Upload a CSV with `Top queries` / `Query` and optionally `Page`, `Clicks`, `Impressions`, `CTR`, `Position`. The importer normalizes headers, removes empty query rows, parses percentages and retains query/page pairs for possible cannibalization review.

For API access, enable the Search Console API, create a Google Cloud service account, grant it access to the relevant Search Console property, and add its JSON fields under `[gcp_service_account]` in Streamlit Secrets. Set the property field in the GSC tab. API requests use query + page dimensions and default to a recent 28-day period ending three days before today; the date range can be selected in the app.

## Optional AI recommendations
Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in Streamlit Secrets or environment variables.

## Data integrity and limitations
- Modifier-based suggestions and intent labels are heuristics, not Google volume / KD / SERP data.
- Multiple ranking URLs for one query are only a review signal, not automatically a cannibalization problem.
- Competitor comparison inspects public page metadata; it does not infer competitor traffic.
- Backlink and rank CSVs are currently preview-only; provider adapters and historical tracking remain future work.
- SQLite is a lightweight prototype store, not a production multi-user database.

Respect robots.txt, site terms and API limits. Store secrets only in environment variables or deployment secrets.

## License
MIT.
