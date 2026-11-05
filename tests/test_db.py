import sqlite3
from src import db


def test_init_db_migrates_legacy_keyword_table_without_losing_rows(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.sqlite3"
    monkeypatch.setattr(db, "DB", database_path)

    connection = sqlite3.connect(database_path)
    connection.executescript("""
        CREATE TABLE projects(id INTEGER PRIMARY KEY, name TEXT NOT NULL, url TEXT UNIQUE NOT NULL);
        CREATE TABLE keywords(
            id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, keyword TEXT NOT NULL,
            intent TEXT, source TEXT, UNIQUE(project_id, keyword)
        );
        CREATE TABLE audits(
            id INTEGER PRIMARY KEY, project_id INTEGER, score INTEGER,
            summary TEXT, checks TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO projects(id, name, url) VALUES(1, 'ResearchUtility', 'https://researchutility.com');
        INSERT INTO keywords(project_id, keyword, intent, source)
        VALUES(1, 'molarity calculator', 'Mixed', 'Seed keyword');
    """)
    connection.commit()
    connection.close()

    db.init_db()
    rows = db.get_keywords(1)
    assert len(rows) == 1
    assert rows[0]["keyword"] == "molarity calculator"
    assert rows[0]["cluster"] == ""
    assert "target_url" in rows[0]


def test_gsc_import_round_trip_and_legacy_cleanup(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "test.sqlite3")
    db.init_db()
    db.add_project("ResearchUtility", "https://researchutility.com")
    project_id = db.list_projects()[0]["id"]

    db.save_keywords(project_id, [
        {"keyword": "molarity calculator", "intent": "Mixed", "source": "Seed keyword", "cluster": "molarity calculator"},
        {"keyword": "how to molarity calculator", "intent": "Informational", "source": "Modifier expansion"},
    ])
    assert db.count_legacy_keyword_ideas(project_id) == 1

    db.save_gsc_rows(project_id, [{
        "query": "molarity calculator", "page": "https://researchutility.com/molarity-calculator/",
        "clicks": 8, "impressions": 80, "ctr": .1, "position": 5.2,
    }])
    imported = db.get_latest_gsc_rows(project_id)
    assert len(imported) == 1
    assert imported[0]["impressions"] == 80

    removed = db.remove_legacy_keyword_ideas(project_id)
    assert removed == 1
    assert db.count_legacy_keyword_ideas(project_id) == 0
    assert len(db.get_keywords(project_id)) == 1
