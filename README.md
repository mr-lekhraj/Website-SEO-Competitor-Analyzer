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

## Configuration
Copy `.env.example` to `.env`. Never commit real credentials.

- GSC: create a Google service account, enable the Search Console API, grant the service account access to your property, and set `GOOGLE_APPLICATION_CREDENTIALS` to the JSON key file path.
- AI: set `OPENAI_API_KEY` to enable generated recommendations.

## Data integrity
Keyword volume, difficulty, live rankings and backlink metrics are not fabricated. Keyword suggestions are modifier-based ideas. Connect a real data provider or import provider exports to obtain those metrics. Competitor comparison reads publicly accessible page metadata; it does not estimate competitor traffic.

## Current limitations
GSC API date range is currently a sample window in `src/integrations.py`. Backlink and rank CSVs are currently previewed rather than stored as historical time series. Automated scheduled reporting, authentication, PDF/XLSX exports and commercial SEO-provider adapters are roadmap items.

## Security and responsible use
Respect robots.txt, website terms and provider API limits. Use low request rates. Do not crawl private or authenticated content. Store secrets in environment variables or deployment secrets, not source control.

## License
MIT. See [LICENSE](LICENSE).
