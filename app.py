import streamlit as st
from src.db import init_db, add_project, list_projects, save_keywords, get_keywords, save_audit, get_latest_audit
from src.seo import audit_url
from src.keywords import expand_keywords
from src.competitors import compare_domains, content_gap
from src.reports import build_report
from src.integrations import load_gsc_rows, ai_recommendations

st.set_page_config(page_title="Website SEO & Competitor Analyzer", page_icon="📈", layout="wide")
init_db()
st.title("📈 Website SEO & Competitor Analyzer")
st.caption("Multi-site SEO intelligence • keyword research • competitor insights • technical audits")

with st.sidebar:
    st.header("Your websites")
    with st.form("add_project"):
        name = st.text_input("Project name", placeholder="ResearchUtility")
        url = st.text_input("Website URL", placeholder="https://example.com")
        if st.form_submit_button("Add website", use_container_width=True):
            try:
                add_project(name.strip(), url.strip())
                st.success("Website added.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    projects = list_projects()
    active = st.selectbox("Active website", projects, format_func=lambda p: f"{p['name']} — {p['url']}") if projects else None
    st.divider()
    st.caption("Keep credentials in environment variables or deployment secrets.")

if not active:
    st.info("Add your first website in the sidebar to begin.")
    st.write("Manage multiple domains in one workspace, then run audits and import research data.")
    st.stop()

pid, name, url = active["id"], active["name"], active["url"]
st.subheader(name)
st.write(url)
tabs = st.tabs(["Overview", "Keyword Research", "Competitors & Gaps", "SEO Audit", "Search Console", "Backlinks & Rankings", "AI Recommendations", "Reports"])

with tabs[0]:
    audit = get_latest_audit(pid)
    c1, c2, c3 = st.columns(3)
    c1.metric("Keyword ideas", len(get_keywords(pid)))
    c2.metric("Latest audit score", f"{audit['score']}/100" if audit else "Not audited")
    c3.metric("Workspace", "Multi-site")
    st.markdown("#### Suggested workflow")
    st.write("Run an audit → add seed keywords → compare competitors → import Search Console and provider exports.")
    if audit:
        st.json(audit["summary"])

with tabs[1]:
    seeds = st.text_area("Seed keywords (one per line or comma-separated)", placeholder="molarity calculator\nresearch methodology tools\nacademic citation generator")
    if st.button("Generate keyword ideas"):
        ideas = expand_keywords(seeds)
        save_keywords(pid, ideas)
        st.success(f"Saved {len(ideas)} keyword ideas. Volume and difficulty require a connected provider.")
    rows = get_keywords(pid)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        csv = "keyword,intent,source\n" + "\n".join(f"{r['keyword']},{r['intent']},{r['source']}" for r in rows)
        st.download_button("Download keyword CSV", csv, "keyword-research.csv", "text/csv")

with tabs[2]:
    competitors = st.text_input("Competitor domains (comma-separated)", placeholder="competitor1.com, competitor2.com")
    if st.button("Compare competitor pages"):
        domains = [x.strip() for x in competitors.split(",") if x.strip()]
        st.dataframe(compare_domains(url, domains), use_container_width=True, hide_index=True)
    st.markdown("#### Content gaps")
    own = st.text_area("Your topics or URLs (one per line)")
    others = st.text_area("Competitor topics or URLs (one per line)")
    if st.button("Find missing topics"):
        st.write(content_gap(own, others))

with tabs[3]:
    target = st.text_input("URL to audit", value=url)
    if st.button("Run technical SEO audit"):
        with st.spinner("Fetching public page and checking metadata..."):
            result = audit_url(target)
            save_audit(pid, result)
        st.metric("Audit score", f"{result['score']}/100")
        st.dataframe(result["checks"], use_container_width=True, hide_index=True)
        st.json(result["summary"])

with tabs[4]:
    st.info("Upload a Search Console CSV export, or configure the optional service-account integration.")
    upload = st.file_uploader("Search Console CSV", type=["csv"], key="gsc")
    if upload:
        import pandas as pd
        st.dataframe(pd.read_csv(upload), use_container_width=True)
    if st.button("Test configured GSC connection"):
        rows, message = load_gsc_rows(url)
        st.info(message)
        if rows:
            st.dataframe(rows, use_container_width=True)

with tabs[5]:
    st.caption("Import provider exports. This starter previews the files; historical storage is a roadmap item.")
    for label, key in [("Backlink CSV", "backlinks"), ("Keyword rank CSV", "rankings")]:
        f = st.file_uploader(label, type=["csv"], key=key)
        if f:
            import pandas as pd
            st.dataframe(pd.read_csv(f), use_container_width=True)

with tabs[6]:
    context = st.text_area("Business goals and target audience", placeholder="Target country, audience, products, objectives...")
    if st.button("Generate SEO recommendations"):
        recs, message = ai_recommendations(url, get_latest_audit(pid), context)
        st.info(message)
        for item in recs:
            st.markdown(f"- {item}")

with tabs[7]:
    if st.button("Build project report"):
        report = build_report(name, url, get_keywords(pid), get_latest_audit(pid))
        st.download_button("Download Markdown report", report, "seo-report.md", "text/markdown")
