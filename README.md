# Website SEO Competitor Analyzer

A multi-website SEO research workspace built with Python and Streamlit.

## Included in this starter release
- Multi-website project workspace backed by SQLite
- Seed keyword expansion with search-intent labels
- Public competitor page metadata comparison
- Content-gap comparison from supplied topic/URL lists
- Technical/on-page audit: HTTP status, HTTPS, title, meta description, H1, canonical, robots meta, image alt, internal links and viewport
- Google Search Console CSV import and optional service-account API connection
- Backlink and keyword-rank CSV import foundations
- Optional AI recommendations through OpenAI API
- Markdown report export
- GitHub Actions test workflow

## Quick start
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Add websites from the sidebar. Local data is stored in `data/seo_analyzer.db`.

## Streamlit Community Cloud deployment
1. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with GitHub.
2. Choose **Create app**.
3. Select repository `mr-lekhraj/Website-SEO-Competitor-Analyzer`, branch `main`, and entrypoint `app.py`.
4. Open **Advanced settings** if you need to add API secrets, then deploy.
5. Because this starter app has no user authentication and its SQLite database is shared by all viewers of the same app instance, keep the deployed app private and restrict viewer access. Do not use a public deployment for private client or business data.

## API configuration
For local use, copy `.env.example` to `.env` and set environment variables. For Streamlit Cloud, use the app's **Settings → Secrets** panel instead of committing keys.

Example secrets structure (replace placeholders locally in the Streamlit secrets UI; never commit real credentials):

```toml
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
OPENAI_MODEL = "gpt-4.1-mini"
GSC_PROPERTY = "https://www.example.com/"

[gcp_service_account]
type = "service_account"
project_id = "YOUR_GOOGLE_CLOUD_PROJECT"
private_key_id = "YOUR_PRIVATE_KEY_ID"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
client_email = "YOUR_SERVICE_ACCOUNT_EMAIL"
client_id = "YOUR_CLIENT_ID"
token_uri = "https://oauth2.googleapis.com/token"
```

For Google Search Console:
1. Enable the Search Console API in Google Cloud.
2. Create a service account and add its email as a user on the Search Console property.
3. Add the service-account JSON fields under the `[gcp_service_account]` section of Streamlit secrets.
4. Set `GSC_PROPERTY` to the exact Search Console property identifier. A Domain property uses a value such as `sc-domain:example.com`; a URL-prefix property uses its full URL.
5. The current API example uses a fixed sample date window in `src/integrations.py`; a date-range selector is planned.

## Data integrity
Keyword volume, difficulty, live rankings and backlink metrics are not fabricated. Keyword suggestions are modifier-based ideas. Connect a real data provider or import provider exports to obtain those metrics. Competitor comparison reads publicly accessible page metadata; it does not estimate competitor traffic.

## Current limitations
GSC API date range is currently a sample window. Backlink and rank CSVs are currently previewed rather than stored as historical time series. Automated scheduled reporting, authentication, PDF/XLSX exports and commercial SEO-provider adapters are roadmap items. The SQLite database is a lightweight starter store and is not a production multi-user database.

## Security and responsible use
Respect robots.txt, website terms and provider API limits. Use low request rates. Do not crawl private or authenticated content. Store secrets in environment variables or deployment secrets, not source control. This starter does not include user authentication, project-level authorization, or production-grade persistence.

## License
MIT. See [LICENSE](LICENSE).
