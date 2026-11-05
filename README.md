# Website SEO Competitor Analyzer

A multi-website SEO research workspace built with Python and Streamlit.

## Keyword Research Engine v2.0
- Natural phrase patterns for calculator, generator, builder, tool and general research seeds
- Rule-based search-intent labels (Informational, Commercial, Transactional, Mixed)
- Seed-based keyword grouping plus approximate lexical clusters of Search Console queries
- Editable keyword-to-landing-page mapping
- Search Console CSV normalization for Query / Top queries and optional Page exports
- Query + page cannibalization review flags based on Search Console data
- Persistent GSC query/page imports with clicks, impressions, CTR, position, source and import history
- CSV exports for keyword inventory and normalized GSC data
- Optional removal of v1 auto-generated modifier phrases, while preserving original seed keywords

The keyword generator produces ideas, not validated demand estimates. Search volume, keyword difficulty and CPC remain blank until connected to a real keyword-data provider. Search Console performance metrics are sourced only from uploaded exports or an authorized Search Console connection.

## Other modules
- Multi-website project workspace backed by SQLite
- Competitor page metadata comparison
- Content-gap comparison from supplied topic / URL lists
- Technical/on-page audit: HTTP status, HTTPS, title, meta description, H1, canonical, robots meta, image alt, internal links and viewport
- Backlink and rank-tracking CSV preview foundations
- Optional AI recommendations through OpenAI API
- Markdown report export
- GitHub Actions tests

## Security and public website fetching
- Website audit and competitor snapshot requests accept only HTTP and HTTPS URLs on standard ports.
- DNS answers are checked and the socket is pinned to a validated globally routable IP address; mixed public/private DNS answers are rejected.
- Redirect destinations are revalidated and independently pinned before the next request.
- Environment proxy settings are disabled for these public page fetches.
- Requests use bounded connection/read timeouts and a 2 MiB response-body limit.
- Localhost, private, link-local, reserved and otherwise non-public IP destinations are rejected.

These protections reduce server-side request forgery (SSRF) exposure in the URL-fetching features. Keep the app behind trusted access controls; do not treat URL validation as a replacement for authentication or infrastructure-level egress restrictions.

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
4. This starter has no user authentication and SQLite data is shared by viewers of the same deployment. Keep the app private and do not enter sensitive client data.

## Google Search Console
Upload an actual Search Console CSV containing a `Top queries` / `Queries` / `Query` column and optionally `Page`, `Clicks`, `Impressions`, `CTR`, and `Position`. The previous keyword idea export has columns `keyword,intent,source`; it is not a GSC export and is intentionally rejected by the GSC importer.

The importer normalizes common headers, removes blank query rows, parses percentages and retains query/page pairs for possible cannibalization review. A Queries-only export can populate query metrics, but a query + page export is needed for page mapping and multi-URL checks.

For API access, enable the Search Console API, create a Google Cloud service account, grant it access to the relevant Search Console property, and add its JSON fields under `[gcp_service_account]` in Streamlit Secrets. Set the property field in the GSC tab. API requests use query + page dimensions and default to a recent 28-day period ending three days before today; the date range can be selected in the app. The first API call requests up to 25,000 rows; pagination is not implemented yet.

## Optional AI recommendations
Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in Streamlit Secrets or environment variables.

## Data integrity and limitations
- Modifier-based suggestions and intent labels are heuristics, not Google volume / KD / SERP data.
- Multiple URLs for one query are only a review signal, not automatically a cannibalization problem.
- Competitor comparison inspects public page metadata; it does not infer competitor traffic.
- Backlink and rank CSVs are currently preview-only; provider adapters and historical tracking remain future work.
- SQLite is a lightweight prototype store, not a production multi-user database. The database migration adds new keyword/GSC fields without dropping existing site records or seed terms.

Respect robots.txt, site terms and API limits. Store secrets only in environment variables or deployment secrets.

## License
MIT.
