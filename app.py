import pandas as pd
import streamlit as st
from datetime import date, timedelta

# Import the database module itself so optional helpers added in newer
# deployments do not break app startup while Streamlit Cloud is refreshing files.
from src import db as db_module

init_db = db_module.init_db
add_project = db_module.add_project
list_projects = db_module.list_projects
save_keywords = db_module.save_keywords
get_keywords = db_module.get_keywords
save_keyword_mappings = db_module.save_keyword_mappings
save_gsc_rows = db_module.save_gsc_rows
get_latest_gsc_rows = db_module.get_latest_gsc_rows
save_audit = db_module.save_audit
get_latest_audit = db_module.get_latest_audit
count_legacy_keyword_ideas = getattr(db_module, "count_legacy_keyword_ideas", lambda project_id: 0)
remove_legacy_keyword_ideas = getattr(db_module, "remove_legacy_keyword_ideas", lambda project_id: 0)
from src.seo import audit_url
from src.keywords import expand_keywords, detect_cannibalization, cluster_keywords
from src.gsc import parse_gsc_csv, gsc_api_rows_to_frame
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
        url_input = st.text_input("Website URL", placeholder="https://example.com")
        if st.form_submit_button("Add website", use_container_width=True):
            try:
                add_project(name.strip(), url_input.strip())
                st.success("Website added.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    projects = list_projects()
    active = st.selectbox("Active website", projects, format_func=lambda p: f"{p['name']} — {p['url']}") if projects else None
    st.divider()
    st.caption("Keep API credentials in environment variables or deployment secrets.")

if not active:
    st.info("Add your first website in the sidebar to begin.")
    st.write("Manage multiple domains in one workspace, then run audits and import research data.")
    st.stop()

pid, name, url = active["id"], active["name"], active["url"]
st.subheader(name)
st.write(url)
tabs = st.tabs([
    "Overview", "Keyword Research", "Competitors & Gaps", "SEO Audit",
    "Search Console", "Backlinks & Rankings", "AI Recommendations", "Reports",
])

with tabs[0]:
    audit = get_latest_audit(pid)
    keyword_rows = get_keywords(pid)
    gsc_rows = get_latest_gsc_rows(pid)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tracked keyword ideas", len(keyword_rows))
    c2.metric("Latest audit score", f"{audit['score']}/100" if audit else "Not audited")
    c3.metric("Latest GSC rows", len(gsc_rows))
    c4.metric("Workspace", "Multi-site")
    st.markdown("#### Suggested workflow")
    st.write("Generate natural keyword ideas → map them to landing pages → import Search Console query/page data → review query clusters and possible cannibalization.")
    if audit:
        st.markdown("#### Latest technical audit")
        st.json(audit["summary"])

with tabs[1]:
    st.markdown("#### Keyword Research Engine v2.0")
    st.caption("Natural phrase patterns, intent classification, seed-based clusters and editable landing-page mapping. Search volume and difficulty are never invented.")
    seeds = st.text_area(
        "Seed keywords (one per line or comma-separated)",
        placeholder="molarity calculator\nresearch methodology builder\nacademic citation generator",
        height=130,
    )
    if st.button("Generate v2 keyword ideas", type="primary"):
        ideas = expand_keywords(seeds)
        if ideas:
            save_keywords(pid, ideas)
            st.success(f"Generated and saved {len(ideas)} unique keyword ideas across {len({row['cluster'] for row in ideas})} seed clusters.")
        else:
            st.warning("Enter at least one seed keyword.")

    legacy_count = count_legacy_keyword_ideas(pid)
    if legacy_count:
        with st.expander(f"Older v1 generated phrases ({legacy_count})"):
            st.warning("These were created by the earlier mechanical modifier generator. Seed terms are not included in this cleanup.")
            if st.button("Remove outdated v1 generated variations", key=f"cleanup_legacy_{pid}"):
                removed = remove_legacy_keyword_ideas(pid)
                st.success(f"Removed {removed} old auto-generated variations. Your seed keywords and any v2 phrases remain.")
                st.rerun()

    rows = get_keywords(pid)
    if rows:
        frame = pd.DataFrame(rows)
        st.markdown("#### Keyword inventory")
        metric1, metric2, metric3 = st.columns(3)
        metric1.metric("Unique keywords", len(frame))
        metric2.metric("Seed clusters", frame["cluster"].replace("", pd.NA).nunique())
        metric3.metric("Mapped to a page", int(frame["target_url"].fillna("").str.strip().ne("").sum()))
        editable = frame[["keyword", "intent", "cluster", "target_url"]].copy()
        edited = st.data_editor(
            editable, use_container_width=True, hide_index=True,
            disabled=["keyword", "intent", "cluster"],
            column_config={
                "keyword": st.column_config.TextColumn("Keyword", width="large"),
                "intent": st.column_config.TextColumn("Search intent", width="small"),
                "cluster": st.column_config.TextColumn("Seed cluster", width="medium"),
                "target_url": st.column_config.TextColumn("Target landing-page URL", width="large"),
            },
            key=f"keyword_mapping_editor_{pid}",
        )
        if st.button("Save landing-page mappings"):
            save_keyword_mappings(pid, edited.to_dict(orient="records"))
            st.success("Landing-page mappings saved.")
            st.rerun()
        st.markdown("#### Keyword clusters")
        clusters = frame.groupby("cluster", dropna=False).agg(
            keyword_count=("keyword", "count"),
            mapped_keywords=("target_url", lambda values: values.fillna("").str.strip().ne("").sum()),
        ).reset_index().rename(columns={"cluster": "Seed cluster"})
        st.dataframe(clusters, use_container_width=True, hide_index=True)
        export = frame.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Download keyword inventory CSV", export, "keyword-research-v2.csv", "text/csv")
    else:
        st.info("Add seed keywords above to build your keyword inventory.")

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
    st.markdown("#### Import Google Search Console query data")
    st.caption("Upload a GSC Queries export or a query + page export. Page-level rows are required for possible cannibalization checks.")
    upload = st.file_uploader("Search Console CSV", type=["csv"], key=f"gsc_csv_{pid}")
    if upload and st.button("Import Search Console CSV", key=f"import_gsc_{pid}"):
        try:
            parsed = parse_gsc_csv(upload)
            import_id = save_gsc_rows(pid, parsed.to_dict(orient="records"), source="CSV")
            st.session_state[f"gsc_import_message_{pid}"] = f"Imported {len(parsed)} query/page rows. Import reference: {import_id[:8]}"
        except Exception as exc:
            st.error(f"Could not import this file: {exc}")
    if st.session_state.get(f"gsc_import_message_{pid}"):
        st.success(st.session_state[f"gsc_import_message_{pid}"])

    with st.expander("Connect to the Search Console API (optional)"):
        st.caption("Requires a service account with access to this Search Console property, configured in Streamlit Secrets.")
        property_id = st.text_input("Search Console property ID", value=url, help="For a Domain property use sc-domain:example.com. For a URL-prefix property use the full property URL.")
        default_end = date.today() - timedelta(days=3)
        default_start = default_end - timedelta(days=27)
        date_col1, date_col2 = st.columns(2)
        start_date = date_col1.date_input("Start date", value=default_start, key=f"gsc_start_{pid}")
        end_date = date_col2.date_input("End date", value=default_end, key=f"gsc_end_{pid}")
        if st.button("Fetch GSC query + page data", key=f"fetch_gsc_{pid}"):
            with st.spinner("Requesting Search Console data..."):
                api_rows, message = load_gsc_rows(url, start_date, end_date, property_id)
            st.info(message)
            if api_rows:
                api_frame = gsc_api_rows_to_frame(api_rows)
                save_gsc_rows(pid, api_frame.to_dict(orient="records"), source="Search Console API")
                st.success(f"Saved {len(api_frame)} query/page rows.")

    latest_gsc = get_latest_gsc_rows(pid)
    if latest_gsc:
        gsc_frame = pd.DataFrame(latest_gsc)
        st.markdown("#### Latest Search Console import")
        summary1, summary2, summary3 = st.columns(3)
        summary1.metric("Query / page rows", len(gsc_frame))
        summary2.metric("Total clicks", f"{gsc_frame['clicks'].fillna(0).sum():,.0f}")
        summary3.metric("Total impressions", f"{gsc_frame['impressions'].fillna(0).sum():,.0f}")
        display_frame = gsc_frame.copy()
        display_frame["ctr"] = display_frame["ctr"].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "")
        st.dataframe(display_frame, use_container_width=True, hide_index=True)
        csv_data = gsc_frame.to_csv(index=False).encode("utf-8-sig")
        st.download_button("Download normalized GSC data", csv_data, "gsc-query-page-data.csv", "text/csv")

        st.markdown("#### Search query clusters")
        query_clusters = pd.DataFrame(cluster_keywords(gsc_frame["query"].dropna().tolist(), similarity_threshold=0.4))
        if not query_clusters.empty:
            query_summary = query_clusters.groupby(["cluster_id", "cluster"], as_index=False).agg(
                query_count=("keyword", "count"),
            ).rename(columns={"cluster": "Cluster topic"})
            st.dataframe(query_summary, use_container_width=True, hide_index=True)
        st.caption("These are approximate lexical groupings to help review topic themes, not semantic intent judgments.")

        st.markdown("#### Possible keyword cannibalization")
        findings = detect_cannibalization(latest_gsc)
        if findings:
            st.warning(f"Found {len(findings)} queries with impressions from more than one landing page. Review these manually; this is a diagnostic flag, not proof of a ranking problem.")
            for finding in findings:
                with st.expander(f"{finding['query']} — {finding['page_count']} pages / {finding['impressions']:,.0f} impressions"):
                    st.write(f"Clicks: {finding['clicks']:,.0f}")
                    for page in finding["pages"]:
                        st.write(f"- {page}")
                    st.caption(finding["review_note"])
        else:
            st.info("No multi-page query rows found in the latest import. Upload a GSC query + page export to enable this check.")
    else:
        st.info("No Search Console data imported yet.")

with tabs[5]:
    st.caption("Import provider exports. This starter previews the files; historical storage is a roadmap item.")
    for label, key in [("Backlink CSV", "backlinks"), ("Keyword rank CSV", "rankings")]:
        file = st.file_uploader(label, type=["csv"], key=f"{key}_{pid}")
        if file:
            st.dataframe(pd.read_csv(file), use_container_width=True)

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
