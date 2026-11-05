import sqlite3, json
from pathlib import Path

DB = Path("data/seo_analyzer.db")

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

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
        """)

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
            conn.execute(
                "INSERT OR IGNORE INTO keywords(project_id,keyword,intent,source) VALUES(?,?,?,?)",
                (project_id, row["keyword"], row["intent"], row["source"])
            )

def get_keywords(project_id):
    with connect() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT keyword,intent,source FROM keywords WHERE project_id=? ORDER BY keyword",
            (project_id,)
        )]

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
