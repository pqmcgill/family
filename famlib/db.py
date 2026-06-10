import os
import pathlib
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS people(
  id INTEGER PRIMARY KEY,
  alias TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('adult','kid','other')),
  patterns TEXT NOT NULL DEFAULT '[]',
  active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS todos(
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  owner_id INTEGER REFERENCES people(id),
  due TEXT,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK(status IN ('open','done','dropped','deferred')),
  defer_count INTEGER NOT NULL DEFAULT 0,
  created TEXT NOT NULL,
  resolved TEXT
);
CREATE TABLE IF NOT EXISTS calendar(
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  date TEXT NOT NULL,
  time TEXT,
  who_id INTEGER REFERENCES people(id),
  status TEXT NOT NULL DEFAULT 'scheduled'
    CHECK(status IN ('scheduled','done','cancelled')),
  created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS standing(
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL CHECK(kind IN ('chore','commitment')),
  title TEXT NOT NULL,
  grp TEXT,
  owner_id INTEGER REFERENCES people(id),
  day TEXT,
  time TEXT,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK(status IN ('active','paused','retired')),
  created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS weeks(
  id INTEGER PRIMARY KEY,
  start TEXT UNIQUE NOT NULL,
  created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS week_entries(
  id INTEGER PRIMARY KEY,
  week_id INTEGER NOT NULL REFERENCES weeks(id),
  kind TEXT NOT NULL CHECK(kind IN ('chore','personal','oneoff')),
  title TEXT NOT NULL,
  owner_id INTEGER REFERENCES people(id),
  standing_id INTEGER REFERENCES standing(id),
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK(status IN ('pending','done','skipped')),
  note TEXT,
  done_date TEXT,
  day TEXT,
  todo_id INTEGER REFERENCES todos(id),
  stage TEXT,
  stage_date TEXT
);
CREATE TABLE IF NOT EXISTS chore_memory(
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  last_done TEXT,
  cadence_days REAL,
  times_done INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pulses(
  id INTEGER PRIMARY KEY,
  person_id INTEGER NOT NULL REFERENCES people(id),
  date TEXT NOT NULL,
  rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 10),
  note TEXT,
  UNIQUE(person_id, date)
);
CREATE TABLE IF NOT EXISTS journal(
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  session TEXT NOT NULL CHECK(session IN ('nightly','weekly','capture')),
  kind TEXT NOT NULL CHECK(kind IN ('transcript','summary')),
  text TEXT NOT NULL
);
-- If FTS ever goes stale (writes bypassing triggers): INSERT INTO journal_fts(journal_fts) VALUES ('rebuild');
CREATE VIRTUAL TABLE IF NOT EXISTS journal_fts
  USING fts5(text, content='journal', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS journal_ai AFTER INSERT ON journal BEGIN
  INSERT INTO journal_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS journal_ad AFTER DELETE ON journal BEGIN
  INSERT INTO journal_fts(journal_fts, rowid, text)
    VALUES ('delete', old.id, old.text);
END;
CREATE TRIGGER IF NOT EXISTS journal_au AFTER UPDATE ON journal BEGIN
  INSERT INTO journal_fts(journal_fts, rowid, text)
    VALUES ('delete', old.id, old.text);
  INSERT INTO journal_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TABLE IF NOT EXISTS observations(
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK(status IN ('active','archived'))
);
CREATE TABLE IF NOT EXISTS time_log(
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('personal','couple','family')),
  level TEXT CHECK(level IN ('partial','full')),
  person_id INTEGER REFERENCES people(id),
  note TEXT
);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  source TEXT NOT NULL,
  entity TEXT NOT NULL,
  entity_id INTEGER,
  action TEXT NOT NULL,
  before TEXT,
  after TEXT,
  undone INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS daily_habits(
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','retired')),
  created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS daily_log(
  id INTEGER PRIMARY KEY,
  habit_id INTEGER NOT NULL REFERENCES daily_habits(id),
  date TEXT NOT NULL,
  note TEXT,
  UNIQUE(habit_id, date)
);
"""


def root():
    """Project root; FAM_HOME overrides (used by tests)."""
    return pathlib.Path(os.environ.get(
        "FAM_HOME", pathlib.Path(__file__).resolve().parent.parent))


def db_path():
    return root() / "data" / "family.db"


def _migrate(con):
    """Add columns that CREATE TABLE IF NOT EXISTS won't add to old DBs."""
    cols = {r["name"] for r in con.execute("PRAGMA table_info(week_entries)")}
    if "day" not in cols:
        con.execute("ALTER TABLE week_entries ADD COLUMN day TEXT")
    if "todo_id" not in cols:
        con.execute("ALTER TABLE week_entries ADD COLUMN todo_id INTEGER"
                    " REFERENCES todos(id)")
    if "stage" not in cols:
        con.execute("ALTER TABLE week_entries ADD COLUMN stage TEXT")
        con.execute("ALTER TABLE week_entries ADD COLUMN stage_date TEXT")
    con.commit()


def connect():
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _migrate(con)
    con.execute("PRAGMA foreign_keys = ON")
    return con
