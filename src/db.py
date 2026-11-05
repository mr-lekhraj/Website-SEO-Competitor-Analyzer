import sqlite3, json
from pathlib import Path

DB = Path("data/seo_analyzer.db")


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_columns(conn, table, definitions):
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for name, definition in definitions.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects(
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, url TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS keywords(
            id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, keyword TEXT NOT NULL,
            intent TEXT, source TEXT, UNIQUE(project_id, keyword),
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS audits(
            id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, score INTEGER,
            summary TEXT, checks TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS gsc_query_pages(
            id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, import_id TEXT NOT NULL,
            query TEXT NOT NULL, page TEXT DEFAULT '', clicks REAL DEFAULT 0,
            impressions REAL DEFAULT 0, ctr REAL, position REAL,
            source TEXT DEFAULT 'CSV', imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        CREATE INDEX IF NOT EXISTS idx_gsc_project_import ON gsc_query_pages(project_id, import_id);
        CREATE INDEX IF NOT EXISTS idx_gsc_query ON gsc_query_pages(project_id, query);
        """)
        _ensure_columns(conn, "keywords", {
            "cluster": "TEXT DEFAULT ''",
            "target_url": "TEXT DEFAULT ''",
            "search_volume": "REAL",
            "keyword_difficulty": "REAL",
            "cpc": "REAL",
        })


def add_project(name, url):
    if not name or not url.startswith(("http://", "https://")):
        raise ValueError("Enter a project name and a valid http(s) URL.")
    with connect() as conn:
        conn.execute("INSERT INTO projects(name,url) VALUES(?,?)", (name, url.rstrip("/")))


def list_projects():
    with connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM projects ORDER BY name")]


def save_keywords(project_id, rows):
    with connect() as conn:
        for row in rows:
            conn.execute("""
                INSERT INTO keywords(project_id,keyword,intent,source,cluster,target_url,search_volume,keyword_difficulty,cpc)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(project_id,keyword) DO UPDATE SET
                    intent=excluded.intent,
                    source=excluded.source,
                    cluster=excluded.cluster,
                    target_url=CASE WHEN excluded.target_url <> '' THEN excluded.target_url ELSE keywords.target_url END
            """, (
                project_id, row["keyword"], row.get("intent", "Mixed"), row.get("source", ""),
                row.get("cluster", ""), row.get("target_url", ""), row.get("search_volume"),
                row.get("keyword_difficulty"), row.get("cpc")
            ))


def get_keywords(project_id):
    with connect() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT keyword,intent,source,cluster,target_url,search_volume,keyword_difficulty,cpc FROM keywords WHERE project_id=? ORDER BY cluster,keyword",
            (project_id,)
        )]


def count_legacy_keyword_ideas(project_id):
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM keywords WHERE project_id=? AND source='Modifier expansion'",
            (project_id,)
        ).fetchone()
    return int(row["total"])


def remove_legacy_keyword_ideas(project_id):
    with connect() as conn:
        cursor = conn.execute(
            "DELETE FROM keywords WHERE project_id=? AND source='Modifier expansion'",
            (project_id,)
        )
    return cursor.rowcount


def save_keyword_mappings(project_id, rows):
    with connect() as conn:
        for row in rows:
            conn.execute(
                "UPDATE keywords SET target_url=? WHERE project_id=? AND keyword=?",
                (str(row.get("target_url") or "").strip(), project_id, row["keyword"])
            )


def save_gsc_rows(project_id, rows, source="CSV"):
    import uuid
    import_id = uuid.uuid4().hex
    with connect() as conn:
        for row in rows:
            query = str(row.get("query") or "").strip()
            if not query:
                continue
            page = str(row.get("page") or "").strip()
            clicks = float(row.get("clicks") or 0)
            impressions = float(row.get("impressions") or 0)
            ctr, position = row.get("ctr"), row.get("position")
            conn.execute("""
                INSERT INTO gsc_query_pages(project_id,import_id,query,page,clicks,impressions,ctr,position,source)
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (
                project_id, import_id, query, page, clicks, impressions,
                None if ctr is None else float(ctr),
                None if position is None else float(position), source
            ))
    return import_id


def get_latest_gsc_rows(project_id):
    with connect() as conn:
        latest = conn.execute(
            "SELECT import_id FROM gsc_query_pages WHERE project_id=? ORDER BY imported_at DESC,id DESC LIMIT 1",
            (project_id,)
        ).fetchone()
        if not latest:
            return []
        rows = conn.execute(
            "SELECT query,page,clicks,impressions,ctr,position,source,imported_at FROM gsc_query_pages WHERE project_id=? AND import_id=? ORDER BY impressions DESC",
            (project_id, latest["import_id"])
        ).fetchall()
        return [dict(row) for row in rows]


def save_audit(project_id, result):
    with connect() as conn:
        conn.execute(
            "INSERT INTO audits(project_id,score,summary,checks) VALUES(?,?,?,?)",
            (project_id, result["score"], json.dumps(result["summary"]), json.dumps(result["checks"]))
        )


def get_latest_audit(project_id):
    with connect() as conn:
        row = conn.execute(
            "SELECT score,summary,checks,created_at FROM audits WHERE project_id=? ORDER BY id DESC LIMIT 1",
            (project_id,)
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    result["summary"] = json.loads(result["summary"])
    result["checks"] = json.loads(result["checks"])
    return result
