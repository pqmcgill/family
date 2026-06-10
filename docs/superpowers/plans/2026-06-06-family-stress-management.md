# Family Stress Management System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local-first SQLite-backed CLI (`bin/fam`) plus three Claude Code skills (`/checkin`, `/weekly`, `/capture`) that let two parents run nightly and weekly stress-management sessions with deterministic, privacy-sanitized state.

**Architecture:** All state lives in `data/family.db` (SQLite). A zero-dependency Python package `famlib/` implements domain modules over a shared append-only event log; `bin/fam` is the only interface skills use. Every write appends an event + updates state in one transaction and echoes the written row (`WROTE entity #id: {json}`). Reads are exhaustive-by-construction report commands with counts in every section header. Real names never enter the DB: a gitignored `private/names.txt` map drives sanitization (journal auto-replaces; all other writes refuse mapped names).

**Tech Stack:** Python 3.9 stdlib only (`sqlite3`, `argparse`, `json`, `unittest`), SQLite FTS5, Claude Code skills (markdown).

**Spec:** `docs/superpowers/specs/2026-06-06-family-stress-management-design.md`

**Conventions for all tasks:**
- Run tests from repo root: `python3 -m unittest tests.test_<name> -v`
- Full suite: `python3 -m unittest discover -s tests -v`
- Tests set `FAM_HOME` to a temp dir so the real `data/` is never touched.
- No Python 3.10+ syntax (system Python is 3.9.6).
- Dates are ISO `YYYY-MM-DD` strings everywhere; domain functions take `today`/dates as parameters (never call `date.today()` inside logic) so tests are deterministic. Only the CLI layer supplies real "today".

---

### Task 1: Scaffolding — package, schema, dates, test base

**Files:**
- Create: `.gitignore`
- Create: `bin/fam`
- Create: `famlib/__init__.py` (empty)
- Create: `famlib/db.py`
- Create: `famlib/dates.py`
- Create: `tests/__init__.py` (empty)
- Create: `tests/base.py`
- Test: `tests/test_foundation.py`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
# personal data — never publish
data/
private/
ritual.md

# python
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 2: Write the failing test**

`tests/base.py`:

```python
import os
import tempfile
import unittest


class FamTest(unittest.TestCase):
    """Every test gets a throwaway FAM_HOME so real data is never touched."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["FAM_HOME"] = self.tmp.name
        from famlib import db
        self.con = db.connect()

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()
        del os.environ["FAM_HOME"]
```

`tests/test_foundation.py`:

```python
import os
import unittest
from tests.base import FamTest
from famlib import dates


class TestSchema(FamTest):
    def test_tables_exist(self):
        names = {r[0] for r in self.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for t in ["people", "todos", "calendar", "standing", "weeks",
                  "week_entries", "chore_memory", "pulses", "journal",
                  "observations", "events"]:
            self.assertIn(t, names)

    def test_db_lives_under_fam_home(self):
        from famlib import db
        self.assertTrue(str(db.db_path()).startswith(os.environ["FAM_HOME"]))

    def test_connect_is_idempotent(self):
        from famlib import db
        con2 = db.connect()  # second connect must not fail on CREATE
        con2.close()


class TestDates(unittest.TestCase):
    def test_parse_rejects_garbage(self):
        with self.assertRaises(SystemExit):
            dates.parse("06/06/2026")

    def test_week_start_is_monday(self):
        self.assertEqual(dates.week_start("2026-06-06"), "2026-06-01")  # Sat -> Mon
        self.assertEqual(dates.week_start("2026-06-01"), "2026-06-01")  # Mon -> itself

    def test_days_until(self):
        self.assertEqual(dates.days_until("2026-06-06", "2026-06-20"), 14)

    def test_add_days(self):
        self.assertEqual(dates.add_days("2026-06-06", -7), "2026-05-30")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m unittest tests.test_foundation -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'famlib'`

- [ ] **Step 4: Write minimal implementation**

`famlib/db.py`:

```python
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
  done_date TEXT
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
"""


def root():
    """Project root; FAM_HOME overrides (used by tests)."""
    return pathlib.Path(os.environ.get(
        "FAM_HOME", pathlib.Path(__file__).resolve().parent.parent))


def db_path():
    return root() / "data" / "family.db"


def connect():
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    return con
```

`famlib/dates.py`:

```python
from datetime import date, timedelta


def today():
    return date.today().isoformat()


def parse(s):
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        raise SystemExit("invalid date: %r (expected YYYY-MM-DD)" % (s,))


def week_start(s):
    d = parse(s)
    return (d - timedelta(days=d.weekday())).isoformat()


def days_until(frm, to):
    return (parse(to) - parse(frm)).days


def add_days(s, n):
    return (parse(s) + timedelta(days=n)).isoformat()
```

`bin/fam` (make executable: `chmod +x bin/fam`):

```python
#!/usr/bin/env python3
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from famlib.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
```

(`famlib/cli.py` doesn't exist until Task 14 — that's fine, `bin/fam` isn't under test yet.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.test_foundation -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Commit**

```bash
chmod +x bin/fam
git add .gitignore bin/fam famlib tests
git commit -m "feat: scaffolding — schema, dates, test base"
```

---

### Task 2: Sanitization layer (`famlib/sanitize.py`)

Real names live only in gitignored `private/names.txt` (`Real Name = alias` per line). `sanitize()` replaces mapped names (whole-word, case-insensitive, longest-first) and is used by journal writes. `guard()` refuses text containing a mapped name and is used by every other write.

**Files:**
- Create: `famlib/sanitize.py`
- Test: `tests/test_sanitize.py`

- [ ] **Step 1: Write the failing test**

`tests/test_sanitize.py`:

```python
import os
import pathlib
from tests.base import FamTest
from famlib import sanitize


class TestSanitize(FamTest):
    def write_names(self, content):
        p = pathlib.Path(os.environ["FAM_HOME"]) / "private"
        p.mkdir(parents=True, exist_ok=True)
        (p / "names.txt").write_text(content)

    def test_no_map_file_is_passthrough(self):
        text, n = sanitize.sanitize("hello Bob")
        self.assertEqual((text, n), ("hello Bob", 0))

    def test_replaces_whole_words_case_insensitive(self):
        self.write_names("Robert = P1\n# comment\n\nMargaret Smith = GM\n")
        text, n = sanitize.sanitize("robert called Margaret Smith about Robertson")
        self.assertEqual(text, "P1 called GM about Robertson")  # Robertson untouched
        self.assertEqual(n, 2)

    def test_longest_name_wins(self):
        self.write_names("Ann = P2\nAnn Marie = K1\n")
        text, _ = sanitize.sanitize("Ann Marie and Ann")
        self.assertEqual(text, "K1 and P2")

    def test_guard_refuses_mapped_names(self):
        self.write_names("Robert = P1\n")
        with self.assertRaises(SystemExit) as cm:
            sanitize.guard("call Robert back")
        self.assertIn("P1", str(cm.exception))

    def test_guard_passes_clean_text(self):
        self.write_names("Robert = P1\n")
        sanitize.guard("call P1 back")  # no raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_sanitize -v`
Expected: ERROR — `No module named 'famlib.sanitize'`

- [ ] **Step 3: Write minimal implementation**

`famlib/sanitize.py`:

```python
import re

from famlib import db


def load_map():
    """Parse private/names.txt -> {real_name: alias}. Missing file = empty map."""
    p = db.root() / "private" / "names.txt"
    mapping = {}
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            real, alias = [s.strip() for s in line.split("=", 1)]
            if real and alias:
                mapping[real] = alias
    return mapping


def _pattern(real):
    return re.compile(r"\b" + re.escape(real) + r"\b", re.IGNORECASE)


def sanitize(text):
    """Replace mapped real names with aliases. Returns (text, replacement_count)."""
    count = 0
    for real, alias in sorted(load_map().items(), key=lambda kv: -len(kv[0])):
        text, n = _pattern(real).subn(alias, text)
        count += n
    return text, count


def guard(text):
    """Refuse any text containing a mapped real name (defense in depth)."""
    if text is None:
        return
    for real, alias in load_map().items():
        if _pattern(real).search(text):
            raise SystemExit(
                "refused: input contains a real name; use alias '%s' instead" % alias)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_sanitize -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add famlib/sanitize.py tests/test_sanitize.py
git commit -m "feat: name sanitization layer (private/names.txt)"
```

---

### Task 3: Event log — record, snapshot, undo, integrity check (`famlib/events.py`)

Every domain write calls `record()` with before/after row snapshots inside the same transaction. `undo()` restores the latest event's `before` state via a compensating event. `check()` replays all events into a fresh in-memory DB and diffs every table against live state.

**Files:**
- Create: `famlib/events.py`
- Test: `tests/test_events.py`

- [ ] **Step 1: Write the failing test**

`tests/test_events.py`:

```python
import json
from tests.base import FamTest
from famlib import events


def insert_person(con, alias):
    with con:
        cur = con.execute(
            "INSERT INTO people(alias, role) VALUES (?, 'adult')", (alias,))
        row = events.snapshot(con, "people", cur.lastrowid)
        events.record(con, "manual", "people", cur.lastrowid, "add", None, row)
    return cur.lastrowid


class TestEvents(FamTest):
    def test_record_and_snapshot(self):
        pid = insert_person(self.con, "P1")
        ev = self.con.execute("SELECT * FROM events").fetchone()
        self.assertEqual(ev["entity"], "people")
        self.assertEqual(ev["action"], "add")
        self.assertIsNone(ev["before"])
        self.assertEqual(json.loads(ev["after"])["alias"], "P1")
        self.assertEqual(ev["entity_id"], pid)

    def test_undo_insert_deletes_row(self):
        pid = insert_person(self.con, "P1")
        undone = events.undo(self.con)
        self.assertEqual(len(undone), 1)
        self.assertIsNone(events.snapshot(self.con, "people", pid))
        # original event flagged; an 'undo' event was appended
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM events WHERE action='undo'").fetchone()[0], 1)

    def test_undo_update_restores_before(self):
        pid = insert_person(self.con, "P1")
        before = events.snapshot(self.con, "people", pid)
        with self.con:
            self.con.execute("UPDATE people SET role='kid' WHERE id=?", (pid,))
            after = events.snapshot(self.con, "people", pid)
            events.record(self.con, "manual", "people", pid, "edit", before, after)
        events.undo(self.con)
        self.assertEqual(events.snapshot(self.con, "people", pid)["role"], "adult")

    def test_undo_with_nothing_to_undo(self):
        self.assertEqual(events.undo(self.con), [])

    def test_check_clean(self):
        insert_person(self.con, "P1")
        events.undo(self.con)
        insert_person(self.con, "P2")
        self.assertEqual(events.check(self.con), [])

    def test_check_detects_drift(self):
        insert_person(self.con, "P1")
        with self.con:  # sneaky write that bypasses the event log
            self.con.execute("UPDATE people SET role='kid' WHERE alias='P1'")
        self.assertIn("people", events.check(self.con))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_events -v`
Expected: ERROR — `No module named 'famlib.events'`

- [ ] **Step 3: Write minimal implementation**

`famlib/events.py`:

```python
import json
import sqlite3
from datetime import datetime, timezone

from famlib import db

# Allowlist: events.entity must be one of these table names.
TABLES = ["people", "todos", "calendar", "standing", "weeks", "week_entries",
          "chore_memory", "pulses", "journal", "observations"]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def snapshot(con, table, rowid):
    assert table in TABLES, table
    r = con.execute("SELECT * FROM %s WHERE id=?" % table, (rowid,)).fetchone()
    return dict(r) if r else None


def record(con, source, entity, entity_id, action, before, after):
    assert entity in TABLES, entity
    con.execute(
        "INSERT INTO events(ts, source, entity, entity_id, action, before, after)"
        " VALUES (?,?,?,?,?,?,?)",
        (now(), source, entity, entity_id, action,
         json.dumps(before) if before is not None else None,
         json.dumps(after) if after is not None else None))


def _restore(con, entity, entity_id, state):
    if state is None:
        con.execute("DELETE FROM %s WHERE id=?" % entity, (entity_id,))
    else:
        cols = ",".join(state)
        ph = ",".join("?" * len(state))
        con.execute("INSERT OR REPLACE INTO %s(%s) VALUES (%s)" % (entity, cols, ph),
                    tuple(state.values()))


def undo(con, count=1):
    """Reverse the latest <count> events via compensating events. Returns them."""
    undone = []
    for _ in range(count):
        ev = con.execute(
            "SELECT * FROM events WHERE undone=0 AND action!='undo'"
            " ORDER BY id DESC LIMIT 1").fetchone()
        if ev is None:
            break
        before = json.loads(ev["before"]) if ev["before"] else None
        current = snapshot(con, ev["entity"], ev["entity_id"])
        with con:
            _restore(con, ev["entity"], ev["entity_id"], before)
            record(con, "manual", ev["entity"], ev["entity_id"], "undo",
                   current, before)
            con.execute("UPDATE events SET undone=1 WHERE id=?", (ev["id"],))
        undone.append(dict(ev))
    return undone


def check(con):
    """Replay the event log into a fresh DB; return list of drifted tables."""
    mem = sqlite3.connect(":memory:")
    mem.row_factory = sqlite3.Row
    mem.executescript(db.SCHEMA)
    for ev in con.execute("SELECT * FROM events ORDER BY id"):
        after = json.loads(ev["after"]) if ev["after"] else None
        with mem:
            _restore(mem, ev["entity"], ev["entity_id"], after)
    problems = []
    for t in TABLES:
        live = [dict(r) for r in con.execute("SELECT * FROM %s ORDER BY id" % t)]
        replayed = [dict(r) for r in mem.execute("SELECT * FROM %s ORDER BY id" % t)]
        if live != replayed:
            problems.append(t)
    mem.close()
    return problems
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_events -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add famlib/events.py tests/test_events.py
git commit -m "feat: append-only event log with undo and replay check"
```

---

### Task 4: People registry (`famlib/people.py`)

**Files:**
- Create: `famlib/people.py`
- Test: `tests/test_people.py`

- [ ] **Step 1: Write the failing test**

`tests/test_people.py`:

```python
import os
import pathlib
from tests.base import FamTest
from famlib import people


class TestPeople(FamTest):
    def test_add_and_list(self):
        row = people.add(self.con, "manual", "P1", "adult", patterns=["babe"])
        self.assertEqual(row["alias"], "P1")
        self.assertEqual([p["alias"] for p in people.list_people(self.con)], ["P1"])

    def test_add_rejects_bad_role(self):
        with self.assertRaises(SystemExit):
            people.add(self.con, "manual", "P1", "wizard")

    def test_add_rejects_duplicate_alias(self):
        people.add(self.con, "manual", "P1", "adult")
        with self.assertRaises(SystemExit):
            people.add(self.con, "manual", "P1", "adult")

    def test_resolve_by_alias_and_pattern(self):
        people.add(self.con, "manual", "P2", "adult", patterns=["mama", "babe"])
        self.assertEqual(people.resolve(self.con, "p2")["alias"], "P2")
        self.assertEqual(people.resolve(self.con, "Babe")["alias"], "P2")
        self.assertIsNone(people.resolve(self.con, "stranger"))

    def test_get_id_unknown_person_message_suggests_add(self):
        with self.assertRaises(SystemExit) as cm:
            people.get_id(self.con, "stranger")
        self.assertIn("fam person add", str(cm.exception))

    def test_alias_must_not_be_a_mapped_real_name(self):
        priv = pathlib.Path(os.environ["FAM_HOME"]) / "private"
        priv.mkdir(parents=True)
        (priv / "names.txt").write_text("Robert = P1\n")
        with self.assertRaises(SystemExit):
            people.add(self.con, "manual", "Robert", "adult")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_people -v`
Expected: ERROR — `No module named 'famlib.people'`

- [ ] **Step 3: Write minimal implementation**

`famlib/people.py`:

```python
import json
import sqlite3

from famlib import events, sanitize

ROLES = ("adult", "kid", "other")


def add(con, source, alias, role, patterns=None):
    if role not in ROLES:
        raise SystemExit("invalid role: %r (expected adult|kid|other)" % role)
    sanitize.guard(alias)
    for p in patterns or []:
        sanitize.guard(p)
    try:
        with con:
            cur = con.execute(
                "INSERT INTO people(alias, role, patterns) VALUES (?,?,?)",
                (alias, role, json.dumps(patterns or [])))
            row = events.snapshot(con, "people", cur.lastrowid)
            events.record(con, source, "people", cur.lastrowid, "add", None, row)
    except sqlite3.IntegrityError:
        raise SystemExit("person alias already exists: %s" % alias)
    return row


def list_people(con):
    return [dict(r) for r in con.execute("SELECT * FROM people ORDER BY id")]


def resolve(con, term):
    """Match alias or reference pattern, case-insensitive. None if unknown."""
    t = term.strip().lower()
    for r in con.execute("SELECT * FROM people WHERE active=1"):
        if r["alias"].lower() == t:
            return r
        if t in [p.lower() for p in json.loads(r["patterns"])]:
            return r
    return None


def get_id(con, term):
    r = resolve(con, term)
    if r is None:
        raise SystemExit(
            "unknown person: %r — add with: fam person add <alias>"
            " --role <adult|kid|other>" % term)
    return r["id"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_people -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add famlib/people.py tests/test_people.py
git commit -m "feat: people registry with aliases, roles, reference patterns"
```

---

### Task 5: To-dos (`famlib/todos.py`)

Statuses: `open` (active), `done`, `dropped`, `deferred` (parked indefinitely — still surfaced by horizon). `defer(to=DATE)` keeps it open with a new due date and bumps `defer_count`; `defer()` with no date parks it.

**Files:**
- Create: `famlib/todos.py`
- Test: `tests/test_todos.py`

- [ ] **Step 1: Write the failing test**

`tests/test_todos.py`:

```python
from tests.base import FamTest
from famlib import people, todos


class TestTodos(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "P1", "adult")

    def test_add_minimal(self):
        row = todos.add(self.con, "manual", "call plumber", today="2026-06-06")
        self.assertEqual(row["status"], "open")
        self.assertIsNone(row["owner_id"])
        self.assertEqual(row["created"], "2026-06-06")

    def test_add_with_owner_and_due(self):
        row = todos.add(self.con, "manual", "renew passport", owner="P1",
                        due="2026-10-01", today="2026-06-06")
        self.assertEqual(row["due"], "2026-10-01")
        self.assertEqual(row["owner_id"], 1)

    def test_add_unknown_owner_fails(self):
        with self.assertRaises(SystemExit):
            todos.add(self.con, "manual", "x", owner="ghost", today="2026-06-06")

    def test_add_bad_due_fails(self):
        with self.assertRaises(SystemExit):
            todos.add(self.con, "manual", "x", due="soon", today="2026-06-06")

    def test_done_sets_status_and_resolved(self):
        row = todos.add(self.con, "manual", "x", today="2026-06-06")
        row = todos.done(self.con, "manual", row["id"], today="2026-06-07")
        self.assertEqual((row["status"], row["resolved"]), ("done", "2026-06-07"))

    def test_done_missing_id_fails(self):
        with self.assertRaises(SystemExit):
            todos.done(self.con, "manual", 999, today="2026-06-06")

    def test_defer_to_date_keeps_open_and_counts(self):
        row = todos.add(self.con, "manual", "x", due="2026-06-10", today="2026-06-06")
        row = todos.defer(self.con, "manual", row["id"], to="2026-06-20")
        self.assertEqual(row["status"], "open")
        self.assertEqual(row["due"], "2026-06-20")
        self.assertEqual(row["defer_count"], 1)

    def test_defer_without_date_parks(self):
        row = todos.add(self.con, "manual", "x", today="2026-06-06")
        row = todos.defer(self.con, "manual", row["id"])
        self.assertEqual(row["status"], "deferred")

    def test_list_open_excludes_resolved(self):
        a = todos.add(self.con, "manual", "a", today="2026-06-06")
        todos.add(self.con, "manual", "b", today="2026-06-06")
        todos.done(self.con, "manual", a["id"], today="2026-06-06")
        self.assertEqual([t["title"] for t in todos.list_open(self.con)], ["b"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_todos -v`
Expected: ERROR — `No module named 'famlib.todos'`

- [ ] **Step 3: Write minimal implementation**

`famlib/todos.py`:

```python
from famlib import dates, events, people, sanitize


def add(con, source, title, owner=None, due=None, today=None):
    sanitize.guard(title)
    if due:
        dates.parse(due)
    owner_id = people.get_id(con, owner) if owner else None
    with con:
        cur = con.execute(
            "INSERT INTO todos(title, owner_id, due, created) VALUES (?,?,?,?)",
            (title, owner_id, due, today or dates.today()))
        row = events.snapshot(con, "todos", cur.lastrowid)
        events.record(con, source, "todos", cur.lastrowid, "add", None, row)
    return row


def _require(con, tid):
    row = events.snapshot(con, "todos", tid)
    if row is None:
        raise SystemExit("no todo #%s" % tid)
    return row


def _set_status(con, source, tid, status, today):
    before = _require(con, tid)
    with con:
        con.execute("UPDATE todos SET status=?, resolved=? WHERE id=?",
                    (status, today, tid))
        after = events.snapshot(con, "todos", tid)
        events.record(con, source, "todos", tid, status, before, after)
    return after


def done(con, source, tid, today=None):
    return _set_status(con, source, tid, "done", today or dates.today())


def drop(con, source, tid, today=None):
    return _set_status(con, source, tid, "dropped", today or dates.today())


def defer(con, source, tid, to=None):
    before = _require(con, tid)
    with con:
        if to:
            dates.parse(to)
            con.execute(
                "UPDATE todos SET due=?, defer_count=defer_count+1 WHERE id=?",
                (to, tid))
        else:
            con.execute(
                "UPDATE todos SET status='deferred', defer_count=defer_count+1"
                " WHERE id=?", (tid,))
        after = events.snapshot(con, "todos", tid)
        events.record(con, source, "todos", tid, "defer", before, after)
    return after


def list_open(con):
    return [dict(r) for r in con.execute(
        "SELECT * FROM todos WHERE status='open' ORDER BY due IS NULL, due, id")]


def list_parked(con):
    return [dict(r) for r in con.execute(
        "SELECT * FROM todos WHERE status='deferred' ORDER BY id")]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_todos -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add famlib/todos.py tests/test_todos.py
git commit -m "feat: todos with defer tracking and parked state"
```

---

### Task 6: Calendar (`famlib/calendar_items.py`)

Named `calendar_items.py` to avoid shadowing stdlib `calendar` (table stays `calendar`).

**Files:**
- Create: `famlib/calendar_items.py`
- Test: `tests/test_calendar.py`

- [ ] **Step 1: Write the failing test**

`tests/test_calendar.py`:

```python
from tests.base import FamTest
from famlib import calendar_items as cal
from famlib import people


class TestCalendar(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "K1", "kid")

    def test_add_requires_valid_date(self):
        with self.assertRaises(SystemExit):
            cal.add(self.con, "manual", "dentist", date="tomorrow",
                    today="2026-06-06")

    def test_add_full(self):
        row = cal.add(self.con, "manual", "swim class", date="2026-06-09",
                      time="16:00", who="K1", today="2026-06-06")
        self.assertEqual(row["status"], "scheduled")
        self.assertEqual(row["who_id"], 1)

    def test_cancel_and_done(self):
        row = cal.add(self.con, "manual", "x", date="2026-06-09",
                      today="2026-06-06")
        self.assertEqual(
            cal.cancel(self.con, "manual", row["id"])["status"], "cancelled")
        row2 = cal.add(self.con, "manual", "y", date="2026-06-09",
                       today="2026-06-06")
        self.assertEqual(
            cal.done(self.con, "manual", row2["id"])["status"], "done")

    def test_upcoming_window_and_all(self):
        cal.add(self.con, "manual", "near", date="2026-06-10", today="2026-06-06")
        cal.add(self.con, "manual", "far", date="2026-09-01", today="2026-06-06")
        cal.add(self.con, "manual", "past", date="2026-06-01", today="2026-06-06")
        near = cal.upcoming(self.con, "2026-06-06", days=14)
        self.assertEqual([r["title"] for r in near], ["near"])
        allfuture = cal.upcoming(self.con, "2026-06-06", days=None)
        self.assertEqual([r["title"] for r in allfuture], ["near", "far"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_calendar -v`
Expected: ERROR — `No module named 'famlib.calendar_items'`

- [ ] **Step 3: Write minimal implementation**

`famlib/calendar_items.py`:

```python
from famlib import dates, events, people, sanitize


def add(con, source, title, date, time=None, who=None, today=None):
    sanitize.guard(title)
    dates.parse(date)
    who_id = people.get_id(con, who) if who else None
    with con:
        cur = con.execute(
            "INSERT INTO calendar(title, date, time, who_id, created)"
            " VALUES (?,?,?,?,?)",
            (title, date, time, who_id, today or dates.today()))
        row = events.snapshot(con, "calendar", cur.lastrowid)
        events.record(con, source, "calendar", cur.lastrowid, "add", None, row)
    return row


def _set_status(con, source, cid, status):
    before = events.snapshot(con, "calendar", cid)
    if before is None:
        raise SystemExit("no calendar item #%s" % cid)
    with con:
        con.execute("UPDATE calendar SET status=? WHERE id=?", (status, cid))
        after = events.snapshot(con, "calendar", cid)
        events.record(con, source, "calendar", cid, status, before, after)
    return after


def done(con, source, cid):
    return _set_status(con, source, cid, "done")


def cancel(con, source, cid):
    return _set_status(con, source, cid, "cancelled")


def upcoming(con, today, days=14):
    """Scheduled items from today forward; days=None means no upper bound."""
    q = "SELECT * FROM calendar WHERE status='scheduled' AND date >= ?"
    args = [today]
    if days is not None:
        q += " AND date <= ?"
        args.append(dates.add_days(today, days))
    q += " ORDER BY date, time IS NULL, time, id"
    return [dict(r) for r in con.execute(q, args)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_calendar -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add famlib/calendar_items.py tests/test_calendar.py
git commit -m "feat: local-only calendar items"
```

---

### Task 7: Chore memory & neglect (`famlib/chores.py`)

`touch()` is called whenever a chore-kind week entry is done: updates `last_done`, bumps `times_done`, learns cadence as an even blend of old cadence and the latest interval. Neglect = `days_since > cadence * 1.5`.

**Files:**
- Create: `famlib/chores.py`
- Test: `tests/test_chores.py`

- [ ] **Step 1: Write the failing test**

`tests/test_chores.py`:

```python
from tests.base import FamTest
from famlib import chores


class TestChores(FamTest):
    def test_touch_creates_then_learns_cadence(self):
        chores.touch(self.con, "manual", "laundry: towels", "2026-06-01")
        r = self.con.execute("SELECT * FROM chore_memory").fetchone()
        self.assertEqual((r["times_done"], r["cadence_days"]), (1, None))
        chores.touch(self.con, "manual", "laundry: towels", "2026-06-08")
        r = self.con.execute("SELECT * FROM chore_memory").fetchone()
        self.assertEqual(r["cadence_days"], 7.0)  # first interval becomes cadence
        chores.touch(self.con, "manual", "laundry: towels", "2026-06-11")
        r = self.con.execute("SELECT * FROM chore_memory").fetchone()
        self.assertEqual(r["cadence_days"], 5.0)  # blend: 0.5*7 + 0.5*3
        self.assertEqual(r["last_done"], "2026-06-11")

    def test_set_cadence_declares_explicitly(self):
        chores.touch(self.con, "manual", "bedding", "2026-06-01")
        chores.set_cadence(self.con, "manual", "bedding", 14)
        r = self.con.execute("SELECT * FROM chore_memory").fetchone()
        self.assertEqual(r["cadence_days"], 14.0)

    def test_set_cadence_unknown_chore_fails(self):
        with self.assertRaises(SystemExit):
            chores.set_cadence(self.con, "manual", "ghost", 7)

    def test_neglected_flags_only_past_threshold(self):
        chores.touch(self.con, "manual", "bedding", "2026-05-01")
        chores.set_cadence(self.con, "manual", "bedding", 14)
        chores.touch(self.con, "manual", "dishes", "2026-06-05")
        chores.set_cadence(self.con, "manual", "dishes", 1)
        flagged = chores.neglected(self.con, "2026-06-06")
        names = [f["name"] for f in flagged]
        self.assertIn("bedding", names)       # 36 days > 14*1.5
        self.assertNotIn("dishes", names)     # 1 day  <= 1.5

    def test_no_cadence_means_no_flag(self):
        chores.touch(self.con, "manual", "new thing", "2026-01-01")
        self.assertEqual(chores.neglected(self.con, "2026-06-06"), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_chores -v`
Expected: ERROR — `No module named 'famlib.chores'`

- [ ] **Step 3: Write minimal implementation**

`famlib/chores.py`:

```python
from famlib import dates, events, sanitize


def touch(con, source, name, done_date):
    """Record that a chore happened; learn cadence from observed intervals."""
    sanitize.guard(name)
    dates.parse(done_date)
    r = con.execute("SELECT * FROM chore_memory WHERE name=?", (name,)).fetchone()
    with con:
        if r is None:
            cur = con.execute(
                "INSERT INTO chore_memory(name, last_done, times_done)"
                " VALUES (?,?,1)", (name, done_date))
            row = events.snapshot(con, "chore_memory", cur.lastrowid)
            events.record(con, source, "chore_memory", cur.lastrowid,
                          "add", None, row)
            return row
        before = dict(r)
        cadence = before["cadence_days"]
        if before["last_done"]:
            interval = dates.days_until(before["last_done"], done_date)
            if interval > 0:
                cadence = float(interval) if cadence is None \
                    else 0.5 * cadence + 0.5 * interval
        con.execute(
            "UPDATE chore_memory SET last_done=?, times_done=times_done+1,"
            " cadence_days=? WHERE id=?", (done_date, cadence, before["id"]))
        after = events.snapshot(con, "chore_memory", before["id"])
        events.record(con, source, "chore_memory", before["id"],
                      "touch", before, after)
    return after


def set_cadence(con, source, name, days):
    r = con.execute("SELECT * FROM chore_memory WHERE name=?", (name,)).fetchone()
    if r is None:
        raise SystemExit("no chore named %r in chore memory" % name)
    before = dict(r)
    with con:
        con.execute("UPDATE chore_memory SET cadence_days=? WHERE id=?",
                    (float(days), before["id"]))
        after = events.snapshot(con, "chore_memory", before["id"])
        events.record(con, source, "chore_memory", before["id"],
                      "cadence", before, after)
    return after


def neglected(con, today):
    """Chores whose days-since-done exceeds 1.5x their cadence."""
    out = []
    for r in con.execute("SELECT * FROM chore_memory ORDER BY name"):
        if not r["last_done"] or not r["cadence_days"]:
            continue
        since = dates.days_until(r["last_done"], today)
        if since > r["cadence_days"] * 1.5:
            out.append({"name": r["name"], "days_since": since,
                        "cadence_days": round(r["cadence_days"], 1)})
    return out


def list_all(con):
    return [dict(r) for r in con.execute(
        "SELECT * FROM chore_memory ORDER BY name")]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_chores -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add famlib/chores.py tests/test_chores.py
git commit -m "feat: chore memory with learned cadence and neglect flags"
```

---

### Task 8: Standing items (`famlib/standing.py`)

**Files:**
- Create: `famlib/standing.py`
- Test: `tests/test_standing.py`

- [ ] **Step 1: Write the failing test**

`tests/test_standing.py`:

```python
from tests.base import FamTest
from famlib import people, standing


class TestStanding(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "P1", "adult")

    def test_add_chore_with_group(self):
        row = standing.add(self.con, "manual", "laundry: K1 clothes",
                           kind="chore", grp="laundry", owner="P1",
                           today="2026-06-06")
        self.assertEqual((row["kind"], row["grp"], row["status"]),
                         ("chore", "laundry", "active"))

    def test_add_commitment_with_day_time(self):
        row = standing.add(self.con, "manual", "K1 swim class",
                           kind="commitment", day="tue", time="16:00",
                           today="2026-06-06")
        self.assertEqual((row["day"], row["time"]), ("tue", "16:00"))

    def test_add_rejects_bad_kind_and_day(self):
        with self.assertRaises(SystemExit):
            standing.add(self.con, "manual", "x", kind="ritual",
                         today="2026-06-06")
        with self.assertRaises(SystemExit):
            standing.add(self.con, "manual", "x", kind="commitment",
                         day="someday", today="2026-06-06")

    def test_pause_resume_retire(self):
        row = standing.add(self.con, "manual", "x", kind="chore",
                           today="2026-06-06")
        self.assertEqual(
            standing.set_status(self.con, "manual", row["id"], "paused")["status"],
            "paused")
        self.assertEqual(
            standing.set_status(self.con, "manual", row["id"], "active")["status"],
            "active")
        self.assertEqual(
            standing.set_status(self.con, "manual", row["id"], "retired")["status"],
            "retired")

    def test_list_active_filters(self):
        a = standing.add(self.con, "manual", "a", kind="chore", today="2026-06-06")
        standing.add(self.con, "manual", "b", kind="chore", today="2026-06-06")
        standing.set_status(self.con, "manual", a["id"], "retired")
        self.assertEqual(
            [s["title"] for s in standing.list_items(self.con, status="active")],
            ["b"])
        self.assertEqual(len(standing.list_items(self.con)), 2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_standing -v`
Expected: ERROR — `No module named 'famlib.standing'`

- [ ] **Step 3: Write minimal implementation**

`famlib/standing.py`:

```python
from famlib import dates, events, people, sanitize

KINDS = ("chore", "commitment")
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
STATUSES = ("active", "paused", "retired")


def add(con, source, title, kind, grp=None, owner=None, day=None, time=None,
        today=None):
    sanitize.guard(title)
    if kind not in KINDS:
        raise SystemExit("invalid kind: %r (expected chore|commitment)" % kind)
    if day is not None and day not in DAYS:
        raise SystemExit("invalid day: %r (expected mon..sun)" % day)
    owner_id = people.get_id(con, owner) if owner else None
    with con:
        cur = con.execute(
            "INSERT INTO standing(kind, title, grp, owner_id, day, time, created)"
            " VALUES (?,?,?,?,?,?,?)",
            (kind, title, grp, owner_id, day, time, today or dates.today()))
        row = events.snapshot(con, "standing", cur.lastrowid)
        events.record(con, source, "standing", cur.lastrowid, "add", None, row)
    return row


def set_status(con, source, sid, status):
    if status not in STATUSES:
        raise SystemExit("invalid status: %r" % status)
    before = events.snapshot(con, "standing", sid)
    if before is None:
        raise SystemExit("no standing item #%s" % sid)
    with con:
        con.execute("UPDATE standing SET status=? WHERE id=?", (status, sid))
        after = events.snapshot(con, "standing", sid)
        events.record(con, source, "standing", sid, status, before, after)
    return after


def list_items(con, status=None, kind=None):
    q, args = "SELECT * FROM standing WHERE 1=1", []
    if status:
        q += " AND status=?"
        args.append(status)
    if kind:
        q += " AND kind=?"
        args.append(kind)
    return [dict(r) for r in con.execute(q + " ORDER BY kind, grp, id", args)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_standing -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add famlib/standing.py tests/test_standing.py
git commit -m "feat: standing items (recurring chores and fixed commitments)"
```

---

### Task 9: Week plans (`famlib/weeks.py`)

`new_week()` drafts entries from active standing chores (the pre-fill). Completing a chore-kind entry touches chore memory. Skipping/modifying an entry never changes the standing item.

**Files:**
- Create: `famlib/weeks.py`
- Test: `tests/test_weeks.py`

- [ ] **Step 1: Write the failing test**

`tests/test_weeks.py`:

```python
from tests.base import FamTest
from famlib import people, standing, weeks


class TestWeeks(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "P1", "adult")
        people.add(self.con, "manual", "P2", "adult")
        standing.add(self.con, "manual", "laundry: towels", kind="chore",
                     grp="laundry", owner="P1", today="2026-06-01")
        standing.add(self.con, "manual", "groceries", kind="chore",
                     owner="P2", today="2026-06-01")
        standing.add(self.con, "manual", "K1 swim", kind="commitment",
                     day="tue", time="16:00", today="2026-06-01")

    def test_new_week_drafts_from_active_standing_chores_only(self):
        wid, start = weeks.new_week(self.con, "weekly", today="2026-06-06")
        self.assertEqual(start, "2026-06-01")
        entries = weeks.entries(self.con, wid)
        self.assertEqual([e["title"] for e in entries],
                         ["laundry: towels", "groceries"])  # no commitment
        self.assertTrue(all(e["standing_id"] for e in entries))

    def test_paused_standing_not_drafted(self):
        s = standing.list_items(self.con, kind="chore")[0]
        standing.set_status(self.con, "manual", s["id"], "paused")
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        self.assertEqual([e["title"] for e in weeks.entries(self.con, wid)],
                         ["groceries"])

    def test_duplicate_week_fails(self):
        weeks.new_week(self.con, "weekly", today="2026-06-06")
        with self.assertRaises(SystemExit):
            weeks.new_week(self.con, "weekly", today="2026-06-06")

    def test_add_variable_entry(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        e = weeks.add_entry(self.con, "weekly", wid, kind="personal",
                            title="P2 pottery night", owner="P2")
        self.assertEqual((e["kind"], e["standing_id"]), ("personal", None))

    def test_entry_done_touches_chore_memory(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        entry = weeks.entries(self.con, wid)[0]
        weeks.entry_done(self.con, "nightly", entry["id"], date="2026-06-03")
        r = self.con.execute(
            "SELECT * FROM chore_memory WHERE name='laundry: towels'").fetchone()
        self.assertEqual(r["last_done"], "2026-06-03")

    def test_personal_entry_done_does_not_touch_chores(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        e = weeks.add_entry(self.con, "weekly", wid, kind="personal",
                            title="gym", owner="P1")
        weeks.entry_done(self.con, "nightly", e["id"], date="2026-06-03")
        self.assertIsNone(self.con.execute(
            "SELECT * FROM chore_memory WHERE name='gym'").fetchone())

    def test_skip_does_not_alter_standing(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        entry = weeks.entries(self.con, wid)[0]
        weeks.entry_skip(self.con, "nightly", entry["id"])
        s = self.con.execute("SELECT status FROM standing WHERE id=?",
                             (entry["standing_id"],)).fetchone()
        self.assertEqual(s["status"], "active")

    def test_week_for_finds_current(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        self.assertEqual(weeks.week_for(self.con, "2026-06-04")["id"], wid)
        self.assertIsNone(weeks.week_for(self.con, "2026-06-10"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_weeks -v`
Expected: ERROR — `No module named 'famlib.weeks'`

- [ ] **Step 3: Write minimal implementation**

`famlib/weeks.py`:

```python
from famlib import chores, dates, events, people, sanitize

ENTRY_KINDS = ("chore", "personal", "oneoff")


def new_week(con, source, start=None, today=None):
    """Create a week and draft entries from active standing chores."""
    start = dates.week_start(start or today or dates.today())
    if con.execute("SELECT 1 FROM weeks WHERE start=?", (start,)).fetchone():
        raise SystemExit("week %s already exists" % start)
    with con:
        cur = con.execute("INSERT INTO weeks(start, created) VALUES (?,?)",
                          (start, today or dates.today()))
        wid = cur.lastrowid
        events.record(con, source, "weeks", wid, "add", None,
                      events.snapshot(con, "weeks", wid))
        for s in con.execute(
                "SELECT * FROM standing WHERE status='active' AND kind='chore'"
                " ORDER BY grp, id"):
            c2 = con.execute(
                "INSERT INTO week_entries(week_id, kind, title, owner_id,"
                " standing_id) VALUES (?, 'chore', ?, ?, ?)",
                (wid, s["title"], s["owner_id"], s["id"]))
            events.record(con, source, "week_entries", c2.lastrowid, "draft",
                          None, events.snapshot(con, "week_entries", c2.lastrowid))
    return wid, start


def week_for(con, date_):
    start = dates.week_start(date_)
    r = con.execute("SELECT * FROM weeks WHERE start=?", (start,)).fetchone()
    return dict(r) if r else None


def entries(con, week_id):
    return [dict(r) for r in con.execute(
        "SELECT * FROM week_entries WHERE week_id=? ORDER BY kind, id",
        (week_id,))]


def add_entry(con, source, week_id, kind, title, owner=None, note=None):
    sanitize.guard(title)
    sanitize.guard(note)
    if kind not in ENTRY_KINDS:
        raise SystemExit("invalid entry kind: %r (chore|personal|oneoff)" % kind)
    if not con.execute("SELECT 1 FROM weeks WHERE id=?", (week_id,)).fetchone():
        raise SystemExit("no week #%s" % week_id)
    owner_id = people.get_id(con, owner) if owner else None
    with con:
        cur = con.execute(
            "INSERT INTO week_entries(week_id, kind, title, owner_id, note)"
            " VALUES (?,?,?,?,?)", (week_id, kind, title, owner_id, note))
        row = events.snapshot(con, "week_entries", cur.lastrowid)
        events.record(con, source, "week_entries", cur.lastrowid, "add",
                      None, row)
    return row


def _set_entry(con, source, eid, status, date_=None):
    before = events.snapshot(con, "week_entries", eid)
    if before is None:
        raise SystemExit("no week entry #%s" % eid)
    with con:
        con.execute("UPDATE week_entries SET status=?, done_date=? WHERE id=?",
                    (status, date_, eid))
        after = events.snapshot(con, "week_entries", eid)
        events.record(con, source, "week_entries", eid, status, before, after)
    return after


def entry_done(con, source, eid, date=None):
    d = date or dates.today()
    after = _set_entry(con, source, eid, "done", d)
    if after["kind"] == "chore":
        chores.touch(con, source, after["title"], d)
    return after


def entry_skip(con, source, eid):
    return _set_entry(con, source, eid, "skipped")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_weeks -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add famlib/weeks.py tests/test_weeks.py
git commit -m "feat: week plans drafted from standing items; done feeds chore memory"
```

---

### Task 10: Pulses (`famlib/pulses.py`)

**Files:**
- Create: `famlib/pulses.py`
- Test: `tests/test_pulses.py`

- [ ] **Step 1: Write the failing test**

`tests/test_pulses.py`:

```python
from tests.base import FamTest
from famlib import people, pulses


class TestPulses(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "P1", "adult")
        people.add(self.con, "manual", "K1", "kid")

    def test_log_basic(self):
        row = pulses.log(self.con, "nightly", "P1", 7, note="long day",
                         date="2026-06-06")
        self.assertEqual((row["rating"], row["note"]), (7, "long day"))

    def test_same_day_relog_overwrites(self):
        pulses.log(self.con, "nightly", "P1", 7, date="2026-06-06")
        pulses.log(self.con, "nightly", "P1", 4, date="2026-06-06")
        rows = self.con.execute("SELECT * FROM pulses").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rating"], 4)

    def test_rating_bounds(self):
        for bad in (0, 11):
            with self.assertRaises(SystemExit):
                pulses.log(self.con, "nightly", "P1", bad, date="2026-06-06")

    def test_adults_only(self):
        with self.assertRaises(SystemExit):
            pulses.log(self.con, "nightly", "K1", 5, date="2026-06-06")

    def test_recent_window(self):
        pulses.log(self.con, "nightly", "P1", 5, date="2026-05-01")
        pulses.log(self.con, "nightly", "P1", 8, date="2026-06-05")
        recent = pulses.recent(self.con, "2026-06-06", days=7)
        self.assertEqual([r["rating"] for r in recent], [8])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_pulses -v`
Expected: ERROR — `No module named 'famlib.pulses'`

- [ ] **Step 3: Write minimal implementation**

`famlib/pulses.py`:

```python
from famlib import dates, events, people, sanitize


def log(con, source, alias, rating, note=None, date=None):
    if not isinstance(rating, int) or not 1 <= rating <= 10:
        raise SystemExit("rating must be an integer 1-10 (10 = great)")
    p = people.resolve(con, alias)
    if p is None:
        raise SystemExit(
            "unknown person: %r — add with: fam person add" % alias)
    if p["role"] != "adult":
        raise SystemExit("pulses are for adults only (%s is %s)"
                         % (p["alias"], p["role"]))
    sanitize.guard(note)
    d = date or dates.today()
    dates.parse(d)
    existing = con.execute(
        "SELECT * FROM pulses WHERE person_id=? AND date=?",
        (p["id"], d)).fetchone()
    with con:
        if existing is None:
            cur = con.execute(
                "INSERT INTO pulses(person_id, date, rating, note)"
                " VALUES (?,?,?,?)", (p["id"], d, rating, note))
            rid = cur.lastrowid
            events.record(con, source, "pulses", rid, "log", None,
                          events.snapshot(con, "pulses", rid))
        else:
            con.execute("UPDATE pulses SET rating=?, note=? WHERE id=?",
                        (rating, note, existing["id"]))
            rid = existing["id"]
            events.record(con, source, "pulses", rid, "log", dict(existing),
                          events.snapshot(con, "pulses", rid))
    return events.snapshot(con, "pulses", rid)


def recent(con, today, days=7):
    cutoff = dates.add_days(today, -days)
    return [dict(r) for r in con.execute(
        "SELECT p.*, ppl.alias FROM pulses p JOIN people ppl"
        " ON p.person_id = ppl.id WHERE p.date > ? AND p.date <= ?"
        " ORDER BY p.date, ppl.alias", (cutoff, today))]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_pulses -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add famlib/pulses.py tests/test_pulses.py
git commit -m "feat: nightly pulse ratings (adults only, one per day)"
```

---

### Task 11: Journal with FTS (`famlib/journal.py`)

Journal is the one write that **auto-sanitizes** (sanitized-verbatim transcripts) instead of refusing.

**Files:**
- Create: `famlib/journal.py`
- Test: `tests/test_journal.py`

- [ ] **Step 1: Write the failing test**

`tests/test_journal.py`:

```python
import os
import pathlib
from tests.base import FamTest
from famlib import journal


class TestJournal(FamTest):
    def test_add_and_search(self):
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text="we talked about the gutters and laundry",
                    date="2026-06-06")
        hits = journal.search(self.con, "gutters")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["date"], "2026-06-06")

    def test_add_sanitizes_real_names(self):
        priv = pathlib.Path(os.environ["FAM_HOME"]) / "private"
        priv.mkdir(parents=True)
        (priv / "names.txt").write_text("Robert = P1\n")
        row, replaced = journal.add(
            self.con, "capture", session="capture", kind="transcript",
            text="Robert said he would do it", date="2026-06-06")
        self.assertEqual(row["text"], "P1 said he would do it")
        self.assertEqual(replaced, 1)

    def test_bad_session_or_kind_fails(self):
        with self.assertRaises(SystemExit):
            journal.add(self.con, "x", session="daily", kind="summary",
                        text="t", date="2026-06-06")
        with self.assertRaises(SystemExit):
            journal.add(self.con, "x", session="nightly", kind="poem",
                        text="t", date="2026-06-06")

    def test_search_no_hits(self):
        self.assertEqual(journal.search(self.con, "unicorn"), [])

    def test_search_handles_quotes(self):
        journal.add(self.con, "x", session="nightly", kind="summary",
                    text='she said "maybe later"', date="2026-06-06")
        self.assertEqual(len(journal.search(self.con, 'maybe "later')), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_journal -v`
Expected: ERROR — `No module named 'famlib.journal'`

- [ ] **Step 3: Write minimal implementation**

`famlib/journal.py`:

```python
from famlib import dates, events, sanitize

SESSIONS = ("nightly", "weekly", "capture")
KINDS = ("transcript", "summary")


def add(con, source, session, kind, text, date=None):
    if session not in SESSIONS:
        raise SystemExit("invalid session: %r (nightly|weekly|capture)" % session)
    if kind not in KINDS:
        raise SystemExit("invalid kind: %r (transcript|summary)" % kind)
    d = date or dates.today()
    dates.parse(d)
    clean, replaced = sanitize.sanitize(text)
    with con:
        cur = con.execute(
            "INSERT INTO journal(date, session, kind, text) VALUES (?,?,?,?)",
            (d, session, kind, clean))
        row = events.snapshot(con, "journal", cur.lastrowid)
        events.record(con, source, "journal", cur.lastrowid, "add", None, row)
    return row, replaced


def search(con, term):
    """FTS5 search over journal text. Term is treated as plain words."""
    words = [w for w in term.replace('"', " ").split() if w]
    if not words:
        return []
    q = " ".join('"%s"' % w for w in words)
    return [dict(r) for r in con.execute(
        "SELECT j.* FROM journal_fts f JOIN journal j ON f.rowid = j.id"
        " WHERE journal_fts MATCH ? ORDER BY j.date", (q,))]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_journal -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add famlib/journal.py tests/test_journal.py
git commit -m "feat: sanitized journal with FTS5 search"
```

---

### Task 12: Observations (`famlib/observations.py`)

**Files:**
- Create: `famlib/observations.py`
- Test: `tests/test_observations.py`

- [ ] **Step 1: Write the failing test**

`tests/test_observations.py`:

```python
from tests.base import FamTest
from famlib import observations as obs


class TestObservations(FamTest):
    def test_add_and_list_active(self):
        obs.add(self.con, "nightly", "chores slip on Thursdays",
                date="2026-06-06")
        active = obs.list_active(self.con)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["text"], "chores slip on Thursdays")

    def test_archive_removes_from_active(self):
        row = obs.add(self.con, "nightly", "x", date="2026-06-06")
        obs.archive(self.con, "nightly", row["id"])
        self.assertEqual(obs.list_active(self.con), [])

    def test_archive_missing_fails(self):
        with self.assertRaises(SystemExit):
            obs.archive(self.con, "nightly", 99)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_observations -v`
Expected: ERROR — `No module named 'famlib.observations'`

- [ ] **Step 3: Write minimal implementation**

`famlib/observations.py`:

```python
from famlib import dates, events, sanitize


def add(con, source, text, date=None):
    sanitize.guard(text)
    d = date or dates.today()
    dates.parse(d)
    with con:
        cur = con.execute(
            "INSERT INTO observations(date, text) VALUES (?,?)", (d, text))
        row = events.snapshot(con, "observations", cur.lastrowid)
        events.record(con, source, "observations", cur.lastrowid, "add",
                      None, row)
    return row


def archive(con, source, oid):
    before = events.snapshot(con, "observations", oid)
    if before is None:
        raise SystemExit("no observation #%s" % oid)
    with con:
        con.execute("UPDATE observations SET status='archived' WHERE id=?",
                    (oid,))
        after = events.snapshot(con, "observations", oid)
        events.record(con, source, "observations", oid, "archive",
                      before, after)
    return after


def list_active(con):
    return [dict(r) for r in con.execute(
        "SELECT * FROM observations WHERE status='active' ORDER BY id")]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_observations -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add famlib/observations.py tests/test_observations.py
git commit -m "feat: observations (saved insights)"
```

---

### Task 13: Reports — checkin, horizon, fair, recall, report (`famlib/reports.py`)

The exhaustive-by-construction reads. **Every section header carries `(N of N shown)`.** `horizon` enumerates every open item regardless of date distance.

**Files:**
- Create: `famlib/reports.py`
- Test: `tests/test_reports.py`

- [ ] **Step 1: Write the failing test**

`tests/test_reports.py`:

```python
from tests.base import FamTest
from famlib import (calendar_items as cal, people, pulses, reports,
                    standing, todos, weeks)


class TestReports(FamTest):
    def setUp(self):
        super().setUp()
        people.add(self.con, "manual", "P1", "adult")
        people.add(self.con, "manual", "P2", "adult")

    def test_checkin_sections_have_counts(self):
        todos.add(self.con, "manual", "call plumber", today="2026-06-06")
        todos.add(self.con, "manual", "renew passport", due="2026-10-01",
                  today="2026-06-06")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("OPEN TODOS (2 of 2 shown)", out)
        self.assertIn("call plumber", out)
        self.assertIn("NO WEEK PLAN", out)

    def test_checkin_shows_week_plan_and_commitments(self):
        standing.add(self.con, "manual", "groceries", kind="chore",
                     owner="P1", today="2026-06-01")
        standing.add(self.con, "manual", "K-swim", kind="commitment",
                     day="tue", time="16:00", today="2026-06-01")
        weeks.new_week(self.con, "weekly", today="2026-06-06")
        out = reports.checkin(self.con, "2026-06-06")
        self.assertIn("WEEK PLAN", out)
        self.assertIn("groceries", out)
        self.assertIn("K-swim", out)
        self.assertIn("(1 of 1 shown)", out)

    def test_horizon_includes_far_future_and_undated_and_parked(self):
        todos.add(self.con, "manual", "far future", due="2027-01-15",
                  today="2026-06-06")
        todos.add(self.con, "manual", "undated thing", today="2026-06-06")
        t = todos.add(self.con, "manual", "parked thing", today="2026-06-06")
        todos.defer(self.con, "manual", t["id"])
        cal.add(self.con, "manual", "wedding", date="2026-12-12",
                today="2026-06-06")
        out = reports.horizon(self.con, "2026-06-06")
        self.assertIn("far future", out)
        self.assertIn("in 223 days", out)      # 2026-06-06 -> 2027-01-15
        self.assertIn("undated thing", out)
        self.assertIn("parked thing", out)
        self.assertIn("wedding", out)
        self.assertIn("DATED ITEMS (2 of 2 shown)", out)

    def test_fair_compares_adults(self):
        wid, _ = weeks.new_week(self.con, "weekly", today="2026-06-06")
        e1 = weeks.add_entry(self.con, "weekly", wid, kind="personal",
                             title="gym", owner="P1")
        weeks.add_entry(self.con, "weekly", wid, kind="personal",
                        title="pottery", owner="P2")
        weeks.entry_done(self.con, "nightly", e1["id"], date="2026-06-03")
        pulses.log(self.con, "nightly", "P1", 8, date="2026-06-05")
        pulses.log(self.con, "nightly", "P2", 4, date="2026-06-05")
        out = reports.fair(self.con, "2026-06-06", weeks_back=4)
        self.assertIn("P1: 1/1 personal blocks", out)
        self.assertIn("P2: 0/1 personal blocks", out)
        self.assertIn("avg pulse 8.0", out)
        self.assertIn("avg pulse 4.0", out)

    def test_recall_searches_structured_and_journal(self):
        from famlib import journal
        todos.add(self.con, "manual", "fix gutters", today="2026-06-06")
        journal.add(self.con, "nightly", session="nightly", kind="summary",
                    text="long chat about gutters", date="2026-06-05")
        out = reports.recall(self.con, "gutters")
        self.assertIn("fix gutters", out)
        self.assertIn("long chat about gutters", out)
        self.assertIn("TODOS (1 of 1 shown)", out)
        self.assertIn("JOURNAL (1 of 1 shown)", out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_reports -v`
Expected: ERROR — `No module named 'famlib.reports'`

- [ ] **Step 3: Write minimal implementation**

`famlib/reports.py`:

```python
from famlib import (calendar_items, chores, dates, journal, observations,
                    people, pulses, standing, todos, weeks)


def _alias(con, pid):
    if pid is None:
        return "-"
    r = con.execute("SELECT alias FROM people WHERE id=?", (pid,)).fetchone()
    return r["alias"] if r else "?"


def _section(title, lines):
    n = len(lines)
    head = "%s (%d of %d shown)" % (title, n, n)
    return [head] + (["  " + l for l in lines] or ["  (none)"])


def _todo_line(con, t, today):
    bits = ["#%d %s" % (t["id"], t["title"]), "@" + _alias(con, t["owner_id"])]
    if t["due"]:
        bits.append("due %s (in %d days)" % (t["due"],
                    dates.days_until(today, t["due"])))
    if t["defer_count"]:
        bits.append("deferred %dx" % t["defer_count"])
    return "  ".join(bits)


def checkin(con, today):
    out = ["NIGHTLY CHECK-IN — %s" % today, ""]
    wk = weeks.week_for(con, today)
    if wk is None:
        out.append("NO WEEK PLAN for week of %s — run /weekly to plan one"
                   % dates.week_start(today))
    else:
        es = weeks.entries(con, wk["id"])
        lines = ["[%s] #%d %s  @%s%s" % (e["status"], e["id"], e["title"],
                 _alias(con, e["owner_id"]),
                 "  (%s)" % e["note"] if e["note"] else "") for e in es]
        out += _section("WEEK PLAN (week of %s)" % wk["start"], lines)
    out.append("")
    comm = standing.list_items(con, status="active", kind="commitment")
    out += _section("STANDING COMMITMENTS", [
        "#%d %s  %s %s  @%s" % (s["id"], s["title"], s["day"] or "?",
                                s["time"] or "", _alias(con, s["owner_id"]))
        for s in comm])
    out.append("")
    out += _section("OPEN TODOS",
                    [_todo_line(con, t, today) for t in todos.list_open(con)])
    out.append("")
    out += _section("CALENDAR NEXT 14 DAYS", [
        "#%d %s  %s %s  @%s" % (c["id"], c["title"], c["date"],
                                c["time"] or "", _alias(con, c["who_id"]))
        for c in calendar_items.upcoming(con, today, days=14)])
    out.append("")
    out += _section("NEGLECT FLAGS", [
        "%s — %d days since last done (usual ~%s days)"
        % (f["name"], f["days_since"], f["cadence_days"])
        for f in chores.neglected(con, today)])
    out.append("")
    out += _section("PULSES LAST 7 DAYS", [
        "%s %s: %d%s" % (p["date"], p["alias"], p["rating"],
                         "  (%s)" % p["note"] if p["note"] else "")
        for p in pulses.recent(con, today, days=7)])
    out.append("")
    out += _section("OBSERVATIONS", [
        "#%d %s" % (o["id"], o["text"]) for o in observations.list_active(con)])
    return "\n".join(out)


def horizon(con, today):
    out = ["FULL HORIZON — %s (everything open, no matter how far out)" % today,
           ""]
    dated = []
    for t in todos.list_open(con):
        if t["due"]:
            dated.append((t["due"], "todo #%d %s  @%s  due %s (in %d days)"
                          % (t["id"], t["title"], _alias(con, t["owner_id"]),
                             t["due"], dates.days_until(today, t["due"]))))
    for c in calendar_items.upcoming(con, today, days=None):
        dated.append((c["date"], "cal  #%d %s  %s %s  @%s (in %d days)"
                      % (c["id"], c["title"], c["date"], c["time"] or "",
                         _alias(con, c["who_id"]),
                         dates.days_until(today, c["date"]))))
    dated.sort(key=lambda x: x[0])
    out += _section("DATED ITEMS", [d[1] for d in dated])
    out.append("")
    out += _section("UNDATED OPEN TODOS", [
        _todo_line(con, t, today) for t in todos.list_open(con)
        if not t["due"]])
    out.append("")
    out += _section("PARKED (deferred indefinitely)", [
        "#%d %s  @%s  deferred %dx" % (t["id"], t["title"],
                                       _alias(con, t["owner_id"]),
                                       t["defer_count"])
        for t in todos.list_parked(con)])
    out.append("")
    out += _section("STANDING ITEMS (active + paused)", [
        "#%d [%s] %s%s  @%s  %s" % (s["id"], s["status"], s["title"],
                                    " (%s)" % s["grp"] if s["grp"] else "",
                                    _alias(con, s["owner_id"]), s["kind"])
        for s in standing.list_items(con) if s["status"] != "retired"])
    out.append("")
    out += _section("CHORE MEMORY", [
        "%s — last done %s, ~every %s days, %dx total"
        % (c["name"], c["last_done"] or "never",
           round(c["cadence_days"], 1) if c["cadence_days"] else "?",
           c["times_done"])
        for c in chores.list_all(con)])
    out.append("")
    out += _section("OBSERVATIONS", [
        "#%d %s" % (o["id"], o["text"]) for o in observations.list_active(con)])
    return "\n".join(out)


def fair(con, today, weeks_back=4):
    cutoff = dates.add_days(today, -7 * weeks_back)
    out = ["FAIRNESS — trailing %d weeks (since %s)" % (weeks_back, cutoff), ""]
    for a in con.execute(
            "SELECT * FROM people WHERE role='adult' AND active=1 ORDER BY id"):
        row = con.execute(
            "SELECT COUNT(*) AS planned,"
            " SUM(CASE WHEN e.status='done' THEN 1 ELSE 0 END) AS done"
            " FROM week_entries e JOIN weeks w ON e.week_id = w.id"
            " WHERE e.kind='personal' AND e.owner_id=? AND w.start >= ?",
            (a["id"], cutoff)).fetchone()
        pr = con.execute(
            "SELECT AVG(rating) AS avg FROM pulses WHERE person_id=?"
            " AND date >= ?", (a["id"], cutoff)).fetchone()
        out.append("%s: %d/%d personal blocks done, avg pulse %s"
                   % (a["alias"], row["done"] or 0, row["planned"],
                      round(pr["avg"], 1) if pr["avg"] is not None else "n/a"))
    return "\n".join(out)


def recall(con, term):
    out = ['RECALL: "%s"' % term, ""]
    like = "%" + term + "%"
    tds = [dict(r) for r in con.execute(
        "SELECT * FROM todos WHERE title LIKE ? ORDER BY id", (like,))]
    out += _section("TODOS", [
        "#%d [%s] %s" % (t["id"], t["status"], t["title"]) for t in tds])
    out.append("")
    obs_hits = [dict(r) for r in con.execute(
        "SELECT * FROM observations WHERE text LIKE ? ORDER BY id", (like,))]
    out += _section("OBSERVATIONS", [
        "#%d [%s] %s" % (o["id"], o["status"], o["text"]) for o in obs_hits])
    out.append("")
    jhits = journal.search(con, term)
    out += _section("JOURNAL", [
        "%s [%s/%s] %s" % (j["date"], j["session"], j["kind"],
                           j["text"][:200].replace("\n", " "))
        for j in jhits])
    return "\n".join(out)


def report(con, today):
    """Human-readable markdown snapshot."""
    return "# Family status — %s\n\n```\n%s\n```\n\n```\n%s\n```\n" % (
        today, checkin(con, today), fair(con, today))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_reports -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add famlib/reports.py tests/test_reports.py
git commit -m "feat: exhaustive reports — checkin, horizon, fair, recall"
```

---

### Task 14: CLI (`famlib/cli.py`) — wiring, init, backup, undo, check

The full command surface. Every write handler prints `WROTE <entity> #<id>: {json}` (the verification echo). `init` creates `data/`, `private/names.txt` and `ritual.md` templates. `backup` copies the DB with a timestamp.

**Files:**
- Create: `famlib/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:

```python
import io
import os
import pathlib
import contextlib
from tests.base import FamTest
from famlib import cli


def run(*argv):
    """Run the CLI capturing stdout; returns (exit_code, output)."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = cli.main(list(argv))
    except SystemExit as e:
        return (e.code if isinstance(e.code, int) else 1), buf.getvalue()
    return code or 0, buf.getvalue()


class TestCli(FamTest):
    def test_init_creates_templates(self):
        code, out = run("init")
        self.assertEqual(code, 0)
        home = pathlib.Path(os.environ["FAM_HOME"])
        self.assertTrue((home / "private" / "names.txt").exists())
        self.assertTrue((home / "ritual.md").exists())
        self.assertTrue((home / "data" / "backups").is_dir())

    def test_person_add_echoes_wrote(self):
        code, out = run("person", "add", "P1", "--role", "adult",
                        "--pattern", "babe")
        self.assertEqual(code, 0)
        self.assertIn("WROTE people #1:", out)
        self.assertIn('"alias": "P1"', out)

    def test_todo_lifecycle_via_cli(self):
        run("person", "add", "P1", "--role", "adult")
        code, out = run("todo", "add", "call plumber", "--who", "P1",
                        "--due", "2026-07-01")
        self.assertIn("WROTE todos #1:", out)
        code, out = run("todo", "done", "1")
        self.assertIn('"status": "done"', out)

    def test_unknown_person_error_is_loud(self):
        code, out = run("todo", "add", "x", "--who", "ghost")
        self.assertNotEqual(code, 0)

    def test_source_flag_recorded(self):
        run("--source", "nightly", "person", "add", "P1", "--role", "adult")
        ev = self.con.execute("SELECT source FROM events").fetchone()
        self.assertEqual(ev["source"], "nightly")

    def test_checkin_and_horizon_run(self):
        run("person", "add", "P1", "--role", "adult")
        run("todo", "add", "far", "--due", "2027-01-01")
        code, out = run("checkin")
        self.assertEqual(code, 0)
        self.assertIn("OPEN TODOS (1 of 1 shown)", out)
        code, out = run("horizon")
        self.assertIn("far", out)

    def test_week_flow_via_cli(self):
        run("person", "add", "P1", "--role", "adult")
        run("standing", "add", "groceries", "--kind", "chore", "--who", "P1")
        code, out = run("week", "new", "--start", "2026-06-01")
        self.assertEqual(code, 0)
        self.assertIn("groceries", out)
        code, out = run("week", "done", "1", "--date", "2026-06-03")
        self.assertIn('"status": "done"', out)

    def test_journal_add_from_arg_and_recall(self):
        code, out = run("journal", "add", "--session", "capture", "--kind",
                        "transcript", "--text", "talked about gutters",
                        "--date", "2026-06-06")
        self.assertIn("WROTE journal #1:", out)
        code, out = run("recall", "gutters")
        self.assertIn("JOURNAL (1 of 1 shown)", out)

    def test_undo_via_cli(self):
        run("person", "add", "P1", "--role", "adult")
        code, out = run("undo")
        self.assertEqual(code, 0)
        self.assertIn("UNDID", out)
        self.assertEqual(self.con.execute(
            "SELECT COUNT(*) FROM people").fetchone()[0], 0)

    def test_check_via_cli(self):
        run("person", "add", "P1", "--role", "adult")
        code, out = run("check")
        self.assertEqual(code, 0)
        self.assertIn("OK", out)

    def test_backup_creates_copy(self):
        run("init")
        code, out = run("backup")
        self.assertEqual(code, 0)
        home = pathlib.Path(os.environ["FAM_HOME"])
        backups = list((home / "data" / "backups").glob("family-*.db"))
        self.assertEqual(len(backups), 1)

    def test_pulse_via_cli(self):
        run("person", "add", "P1", "--role", "adult")
        code, out = run("pulse", "log", "P1", "7", "--note", "ok day",
                        "--date", "2026-06-06")
        self.assertIn("WROTE pulses #1:", out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_cli -v`
Expected: ERROR — `No module named 'famlib.cli'`

- [ ] **Step 3: Write the implementation**

`famlib/cli.py`:

```python
import argparse
import json
import shutil
import sys
from datetime import datetime

from famlib import (calendar_items, chores, dates, db, events, journal,
                    observations, people, pulses, reports, standing, todos,
                    weeks)

NAMES_TEMPLATE = """\
# Real-name -> alias map. THIS FILE IS GITIGNORED — real names live only here.
# Format: Real Name = alias   (one per line, # for comments)
# Example:
#   Robert = P1
#   Margaret Smith = GM
"""

RITUAL_TEMPLATE = """\
# Our Check-in Ritual

This file is read by /checkin and /weekly and evolves through use.
It is GITIGNORED — personal details are safe here.

## Current shape (loose by design — we'll converge over time)

- Open with whatever most needs attention from `fam checkin`.
- Make sure before closing: week plan progress, new todos/calendar items,
  pulse for each adult.
- Keep it conversational. The system facilitates; we do the work.

## Preferences we've settled on

(none yet — they'll accumulate here)
"""


def echo(entity, row):
    print("WROTE %s #%d: %s" % (entity, row["id"],
                                json.dumps(row, ensure_ascii=False)))


def main(argv=None):
    p = argparse.ArgumentParser(prog="fam",
                                description="family stress management CLI")
    p.add_argument("--source", default="manual",
                   choices=["manual", "nightly", "weekly", "transcript",
                            "capture"])
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")
    sub.add_parser("backup")
    sub.add_parser("check")
    u = sub.add_parser("undo")
    u.add_argument("--n", type=int, default=1)

    sub.add_parser("checkin")
    sub.add_parser("horizon")
    sub.add_parser("report")
    f = sub.add_parser("fair")
    f.add_argument("--weeks", type=int, default=4)
    rc = sub.add_parser("recall")
    rc.add_argument("term")

    pp = sub.add_parser("person").add_subparsers(dest="sub", required=True)
    pa = pp.add_parser("add")
    pa.add_argument("alias")
    pa.add_argument("--role", required=True)
    pa.add_argument("--pattern", action="append", default=[])
    pp.add_parser("list")

    tp = sub.add_parser("todo").add_subparsers(dest="sub", required=True)
    ta = tp.add_parser("add")
    ta.add_argument("title")
    ta.add_argument("--who")
    ta.add_argument("--due")
    for name in ("done", "drop"):
        x = tp.add_parser(name)
        x.add_argument("id", type=int)
    td = tp.add_parser("defer")
    td.add_argument("id", type=int)
    td.add_argument("--to")
    tp.add_parser("list")

    cp = sub.add_parser("cal").add_subparsers(dest="sub", required=True)
    ca = cp.add_parser("add")
    ca.add_argument("title")
    ca.add_argument("--date", required=True)
    ca.add_argument("--time")
    ca.add_argument("--who")
    for name in ("done", "cancel"):
        x = cp.add_parser(name)
        x.add_argument("id", type=int)
    cp.add_parser("list")

    sp = sub.add_parser("standing").add_subparsers(dest="sub", required=True)
    sa = sp.add_parser("add")
    sa.add_argument("title")
    sa.add_argument("--kind", required=True)
    sa.add_argument("--group", dest="grp")
    sa.add_argument("--who")
    sa.add_argument("--day")
    sa.add_argument("--time")
    for name in ("pause", "resume", "retire"):
        x = sp.add_parser(name)
        x.add_argument("id", type=int)
    sp.add_parser("list")

    wp = sub.add_parser("week").add_subparsers(dest="sub", required=True)
    wn = wp.add_parser("new")
    wn.add_argument("--start")
    wa = wp.add_parser("add")
    wa.add_argument("title")
    wa.add_argument("--kind", required=True)
    wa.add_argument("--who")
    wa.add_argument("--note")
    wa.add_argument("--week-start")
    wd = wp.add_parser("done")
    wd.add_argument("id", type=int)
    wd.add_argument("--date")
    ws = wp.add_parser("skip")
    ws.add_argument("id", type=int)
    wsh = wp.add_parser("show")
    wsh.add_argument("--start")

    chp = sub.add_parser("chore").add_subparsers(dest="sub", required=True)
    cc = chp.add_parser("cadence")
    cc.add_argument("name")
    cc.add_argument("days", type=float)
    chp.add_parser("list")

    plp = sub.add_parser("pulse").add_subparsers(dest="sub", required=True)
    pl = plp.add_parser("log")
    pl.add_argument("alias")
    pl.add_argument("rating", type=int)
    pl.add_argument("--note")
    pl.add_argument("--date")
    pll = plp.add_parser("list")
    pll.add_argument("--days", type=int, default=7)

    jp = sub.add_parser("journal").add_subparsers(dest="sub", required=True)
    ja = jp.add_parser("add")
    ja.add_argument("--session", required=True)
    ja.add_argument("--kind", required=True)
    ja.add_argument("--text", help="text; omit to read from stdin")
    ja.add_argument("--date")

    op = sub.add_parser("obs").add_subparsers(dest="sub", required=True)
    oa = op.add_parser("add")
    oa.add_argument("text")
    oa.add_argument("--date")
    ox = op.add_parser("archive")
    ox.add_argument("id", type=int)
    op.add_parser("list")

    a = p.parse_args(argv)
    src = a.source
    today = dates.today()

    if a.cmd == "init":
        root = db.root()
        (root / "data" / "backups").mkdir(parents=True, exist_ok=True)
        priv = root / "private"
        priv.mkdir(exist_ok=True)
        if not (priv / "names.txt").exists():
            (priv / "names.txt").write_text(NAMES_TEMPLATE)
        if not (root / "ritual.md").exists():
            (root / "ritual.md").write_text(RITUAL_TEMPLATE)
        db.connect().close()
        print("initialized: data/family.db, private/names.txt, ritual.md")
        return 0

    con = db.connect()
    try:
        if a.cmd == "backup":
            dest = (db.root() / "data" / "backups" / ("family-%s.db"
                    % datetime.now().strftime("%Y%m%d-%H%M%S")))
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(db.db_path()), str(dest))
            print("backed up to %s" % dest)
        elif a.cmd == "check":
            problems = events.check(con)
            if problems:
                print("DRIFT in tables: %s" % ", ".join(problems))
                return 1
            print("OK — event log replays to current state")
        elif a.cmd == "undo":
            undone = events.undo(con, a.n)
            for ev in undone:
                print("UNDID %s #%s %s" % (ev["entity"], ev["entity_id"],
                                           ev["action"]))
            if not undone:
                print("nothing to undo")
        elif a.cmd == "checkin":
            print(reports.checkin(con, today))
        elif a.cmd == "horizon":
            print(reports.horizon(con, today))
        elif a.cmd == "report":
            print(reports.report(con, today))
        elif a.cmd == "fair":
            print(reports.fair(con, today, weeks_back=a.weeks))
        elif a.cmd == "recall":
            print(reports.recall(con, a.term))
        elif a.cmd == "person":
            if a.sub == "add":
                echo("people", people.add(con, src, a.alias, a.role,
                                          patterns=a.pattern))
            else:
                for r in people.list_people(con):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "todo":
            if a.sub == "add":
                echo("todos", todos.add(con, src, a.title, owner=a.who,
                                        due=a.due, today=today))
            elif a.sub == "done":
                echo("todos", todos.done(con, src, a.id, today=today))
            elif a.sub == "drop":
                echo("todos", todos.drop(con, src, a.id, today=today))
            elif a.sub == "defer":
                echo("todos", todos.defer(con, src, a.id, to=a.to))
            else:
                for r in todos.list_open(con) + todos.list_parked(con):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "cal":
            if a.sub == "add":
                echo("calendar", calendar_items.add(
                    con, src, a.title, date=a.date, time=a.time, who=a.who,
                    today=today))
            elif a.sub == "done":
                echo("calendar", calendar_items.done(con, src, a.id))
            elif a.sub == "cancel":
                echo("calendar", calendar_items.cancel(con, src, a.id))
            else:
                for r in calendar_items.upcoming(con, today, days=None):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "standing":
            if a.sub == "add":
                echo("standing", standing.add(
                    con, src, a.title, kind=a.kind, grp=a.grp, owner=a.who,
                    day=a.day, time=a.time, today=today))
            elif a.sub in ("pause", "retire"):
                status = "paused" if a.sub == "pause" else "retired"
                echo("standing", standing.set_status(con, src, a.id, status))
            elif a.sub == "resume":
                echo("standing", standing.set_status(con, src, a.id, "active"))
            else:
                for r in standing.list_items(con):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "week":
            if a.sub == "new":
                wid, start = weeks.new_week(con, src, start=a.start,
                                            today=today)
                print("WROTE weeks #%d: week of %s" % (wid, start))
                for e in weeks.entries(con, wid):
                    echo("week_entries", e)
            elif a.sub == "add":
                wk = weeks.week_for(con, a.week_start or today)
                if wk is None:
                    raise SystemExit("no week plan for that date — run:"
                                     " fam week new")
                echo("week_entries", weeks.add_entry(
                    con, src, wk["id"], kind=a.kind, title=a.title,
                    owner=a.who, note=a.note))
            elif a.sub == "done":
                echo("week_entries", weeks.entry_done(con, src, a.id,
                                                      date=a.date))
            elif a.sub == "skip":
                echo("week_entries", weeks.entry_skip(con, src, a.id))
            else:  # show
                wk = weeks.week_for(con, a.start or today)
                if wk is None:
                    print("no week plan for %s" % (a.start or today))
                else:
                    print("week of %s" % wk["start"])
                    for e in weeks.entries(con, wk["id"]):
                        print(json.dumps(e, ensure_ascii=False))
        elif a.cmd == "chore":
            if a.sub == "cadence":
                echo("chore_memory", chores.set_cadence(con, src, a.name,
                                                        a.days))
            else:
                for r in chores.list_all(con):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "pulse":
            if a.sub == "log":
                echo("pulses", pulses.log(con, src, a.alias, a.rating,
                                          note=a.note, date=a.date))
            else:
                for r in pulses.recent(con, today, days=a.days):
                    print(json.dumps(r, ensure_ascii=False))
        elif a.cmd == "journal":
            text = a.text if a.text is not None else sys.stdin.read()
            row, replaced = journal.add(con, src, session=a.session,
                                        kind=a.kind, text=text, date=a.date)
            echo("journal", row)
            if replaced:
                print("sanitized: %d name(s) replaced with aliases" % replaced)
        elif a.cmd == "obs":
            if a.sub == "add":
                echo("observations", observations.add(con, src, a.text,
                                                      date=a.date))
            elif a.sub == "archive":
                echo("observations", observations.archive(con, src, a.id))
            else:
                for r in observations.list_active(con):
                    print(json.dumps(r, ensure_ascii=False))
        return 0
    finally:
        con.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_cli -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Smoke test the real binary**

```bash
./bin/fam init
./bin/fam person add P1 --role adult
./bin/fam checkin
./bin/fam check
```

Expected: init message; `WROTE people #1: ...`; a checkin report with counted sections; `OK — event log replays to current state`.
Then reset the real data dir (it was only a smoke test): `rm -rf data/ ritual.md private/`

- [ ] **Step 6: Run the full suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add famlib/cli.py tests/test_cli.py
git commit -m "feat: fam CLI — full command surface with write echoes"
```

---

### Task 15: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

````markdown
# Family Check-in System

A local-first, conversational system for two parents to manage household
stress through Claude Code: house cleaning, todos/calendar, and personal
time. Nightly check-ins and weekly planning sessions, backed by SQLite.

The system facilitates us doing the work — it never does the work for us.

## Setup

```bash
./bin/fam init        # creates data/, private/names.txt, ritual.md
```

Then edit `private/names.txt` with your real-name → alias mappings
(this file is gitignored and is the only place real names ever exist).

Add your people:

```bash
./bin/fam person add P1 --role adult --pattern "<nickname>"
./bin/fam person add P2 --role adult
./bin/fam person add K1 --role kid
./bin/fam person add K2 --role kid
```

## Daily use

Open Claude Code in this directory and run:

- `/checkin` — nightly check-in (progress, new items, pulse)
- `/weekly` — weekly review + plan next week
- `/capture` — quick ad-hoc capture (note or transcript), any time

## Direct CLI

`./bin/fam --help` for everything. Highlights:

- `fam checkin` / `fam horizon` — exhaustive state reports (nothing is
  ever silently omitted; every section shows its full count)
- `fam recall <term>` — full-history search, including journals
- `fam undo` — reverse the last write (history is append-only)
- `fam check` — verify the event log replays exactly to current state
- `fam backup` — timestamped DB copy in `data/backups/`

## Privacy

- Real names never enter the database — `private/names.txt` drives
  sanitization before every write; journal text is auto-sanitized.
- `data/`, `private/`, and `ritual.md` are gitignored. Only general
  skill/system code is publishable.
- Before publishing this repo anywhere, verify history: 
  `git log --all -p | grep -i <real names>` should return nothing.

## Architecture

- `famlib/` — zero-dependency Python (stdlib only); SQLite + FTS5
- Append-only event log; every state change is auditable and undoable
- `bin/fam` — the only interface the skills use; deterministic reads
  and writes (the model never recalls state from memory)
- `.claude/skills/` — the conversational layer (checkin/weekly/capture)
- `ritual.md` — the evolving shape of our check-in (converges with use)
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with setup and privacy notes"
```

---

### Task 16: `/checkin` skill

**REQUIRED SUB-SKILL: superpowers:writing-skills.** Invoke it before authoring; follow its testing methodology after.

**Files:**
- Create: `.claude/skills/checkin/SKILL.md`

- [ ] **Step 1: Invoke superpowers:writing-skills and review its guidance**

- [ ] **Step 2: Write the skill (draft below; refine per writing-skills)**

`.claude/skills/checkin/SKILL.md`:

```markdown
---
name: checkin
description: Nightly family check-in — review the week plan, capture updates and new items, log pulses. Use when the user says "check-in", "checkin", or starts the nightly routine.
---

# Nightly Check-in

You are facilitating a nightly check-in between two adults (P1 drives;
sometimes both talk and P1 pastes a transcript). Your job is to
facilitate THEM doing the work — never do it for them, never lecture.

## Hard rules (non-negotiable)

1. **Never recall state from memory.** All state comes from `./bin/fam`
   output in THIS session. All writes go through `./bin/fam` commands.
2. **Propose, then confirm.** Never write anything extracted from
   conversation or a transcript until the user confirms the batch.
   Ambiguity becomes a question, never a guess.
3. **Aliases only.** If a real name appears, resolve it to an alias via
   the people list (`./bin/fam person list`). If the CLI refuses a write
   (real-name guard), replace with the indicated alias and retry. If a
   person is unknown, propose: alias + role -> `fam person add`, and tell
   the user to add the real-name mapping to `private/names.txt` themselves
   (you never write real names to any file).
4. **Facts vs. inference.** CLI output is fact. Your own pattern
   observations must be labeled "I notice ..." and are NOT saved unless
   the user asks (then: `fam obs add "..."`).

## Flow

1. Run `./bin/fam backup`, then `./bin/fam --source nightly checkin`.
2. Read `ritual.md` for the current shape and preferences of the ritual.
3. Open with the 1-2 things that most need attention from the report
   (neglect flags, stale week plan, far-past-due todos). Then follow the
   natural conversation.
4. As things come up, accumulate proposed changes. If the user pastes a
   transcript: parse it, resolve people to aliases, and present the FULL
   list of proposed changes ("From your conversation I'm capturing: ...").
5. Before closing, make sure these were covered (gently, not as a march):
   - week plan progress (`fam week done/skip <entry-id>`)
   - new todos / calendar items
   - pulse for each adult (`fam pulse log <alias> <1-10> --note "..."`)
6. On confirmation, execute the writes with `--source nightly` (or
   `--source transcript` for transcript-derived changes). Save the
   session journal: `./bin/fam --source nightly journal add --session
   nightly --kind transcript --text "<pasted transcript>"` (transcripts)
   and/or `--kind summary` (your concise summary of the live dialogue).
7. **Verification replay:** list every `WROTE ...` echo line against what
   was agreed. Ask the user to confirm it matches. Fix mismatches with
   `./bin/fam undo` + corrected re-entry.

## Self-adjustment

If the users give feedback about how the check-in itself works:
- Ritual/preference changes -> propose an edit to `ritual.md`, show the
  diff, apply on confirmation (do not commit; it's gitignored).
- Behavior changes -> propose an edit to this SKILL.md, show the diff,
  apply on confirmation, then `git add .claude/skills && git commit`.
Keep personal specifics OUT of SKILL.md — they belong in ritual.md.
```

- [ ] **Step 3: Test with a subagent (writing-skills methodology)**

Dispatch a subagent with this scenario and verify behavior:

> You have the checkin skill at .claude/skills/checkin/SKILL.md. The project has a fam CLI at ./bin/fam (initialized, with people P1, P2 added). Simulate: user runs /checkin and pastes this transcript: "ok so I did the towels today. [P2 real-name placeholder] said she wants to call the dentist for K1 sometime next week. Also my mom is visiting on the 20th." Show exactly what you would do.

Verify the subagent: (a) ran backup + checkin first, (b) proposed changes without writing, (c) asked who "my mom" is / proposed a new person, (d) only described writes after confirmation, (e) planned a verification replay. If any check fails, tighten the skill wording and re-test.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/checkin
git commit -m "feat: /checkin nightly skill"
```

---

### Task 17: `/weekly` skill

**REQUIRED SUB-SKILL: superpowers:writing-skills.**

**Files:**
- Create: `.claude/skills/weekly/SKILL.md`

- [ ] **Step 1: Write the skill**

`.claude/skills/weekly/SKILL.md`:

```markdown
---
name: weekly
description: Weekly family review and planning — full horizon sweep, neglect/fairness/trend review, then plan next week from standing items. Use when the user says "weekly", "weekly review", or "plan the week".
---

# Weekly Review & Planning

Same hard rules as the nightly check-in skill (read
`.claude/skills/checkin/SKILL.md` rules section first and apply rules
1-4 identically). Differences are in scope and flow.

## Flow

1. Run `./bin/fam backup`, then:
   - `./bin/fam --source weekly horizon` (EVERY open item, however far out)
   - `./bin/fam --source weekly chore list`
   - `./bin/fam --source weekly fair --weeks 4`
2. Read `ritual.md`.
3. **Review phase** — walk through, conversationally:
   - Far-out dated items: anything that needs action to start now?
   - Parked todos: still parked, or revive/drop?
   - Neglect flags: name them plainly ("bedding is at 24 days, usually 14").
   - Fairness: present the numbers; if lopsided, ask — never accuse.
   - Pulse trends: facts first, then any "I notice ..." inference.
4. **Planning phase** — `./bin/fam --source weekly week new` drafts next
   week from standing chores. Then through conversation:
   - Adjust the draft: skip entries (`fam week skip`), add one-offs.
   - Plan personal time blocks for BOTH adults
     (`fam week add "<block>" --kind personal --who <alias>`).
   - Standing items themselves: anything to add, pause, resume, retire?
5. Save a journal summary (`--session weekly --kind summary`), plus any
   pasted transcript (`--kind transcript`).
6. **Verification replay** — same as nightly: list all WROTE echoes,
   confirm, fix with undo if wrong.

## Self-adjustment

Same mechanism as the checkin skill.
```

- [ ] **Step 2: Test with a subagent**

Scenario: DB has standing chores (two laundry groups, groceries), one far-future todo (due in 5 months), one parked todo, and last week's plan with one skipped entry. Ask the subagent to simulate /weekly. Verify: (a) ran horizon/chore list/fair before any conversation, (b) surfaced the far-future and parked items explicitly, (c) drafted the new week via `fam week new` only during planning phase, (d) asked about personal time for both adults, (e) verification replay planned. Tighten wording if any check fails.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/weekly
git commit -m "feat: /weekly review and planning skill"
```

---

### Task 18: `/capture` skill

**REQUIRED SUB-SKILL: superpowers:writing-skills.**

**Files:**
- Create: `.claude/skills/capture/SKILL.md`

- [ ] **Step 1: Write the skill**

`.claude/skills/capture/SKILL.md`:

```markdown
---
name: capture
description: Quick ad-hoc capture — paste a note or conversation transcript any time; extract state changes, confirm, write, done. Use for "capture this", "add this", or any quick mid-day update outside check-ins.
---

# Quick Capture

Minimal flow — no ritual, no review. Same hard rules as the checkin
skill (read `.claude/skills/checkin/SKILL.md` rules section and apply
rules 1-4 identically).

## Flow

1. Take the user's note or transcript.
2. If you need current state to interpret it (e.g. "mark the towels
   done" needs the entry id), run `./bin/fam --source capture checkin`
   — never guess ids.
3. Propose the extracted changes as a batch. Unknown people -> propose
   `fam person add`. Ambiguity -> ask.
4. On confirmation: execute writes with `--source capture`; store the
   raw input: `./bin/fam --source capture journal add --session capture
   --kind transcript --text "..."` (or `--kind summary` for short notes
   you've restated).
5. Echo the WROTE lines back as confirmation. Done — exit; no pulse, no
   review.
```

- [ ] **Step 2: Test with a subagent**

Scenario: user says `/capture grabbed groceries on the way home, and we need to RSVP to the birthday party by Friday`. Verify: (a) ran checkin to find the groceries week-entry id rather than guessing, (b) proposed both changes + journal write before writing, (c) no pulse/review steps. Tighten if needed.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/capture
git commit -m "feat: /capture ad-hoc skill"
```

---

### Task 19: Final verification & real setup

**Files:** none new

- [ ] **Step 1: Full test suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: ALL PASS (~60 tests)

- [ ] **Step 2: Publication-safety audit**

```bash
git status --porcelain        # data/, private/, ritual.md must NOT appear
git log --all -p | grep -icE "<each real first name>"   # expect 0
```

Expected: tracked files are only code/skills/docs; grep count is 0.

- [ ] **Step 3: Real initialization (the actual household instance)**

```bash
./bin/fam init
./bin/fam check
```

Then tell the user: edit `private/names.txt` with your real-name → alias mappings, then add your four people with `fam person add` (or do it together in the first `/checkin`).

- [ ] **Step 4: Verify against spec checklist**

Confirm each spec requirement has landed: accuracy contract (echo + counts + horizon + undo + check), standing items pre-fill, neglect flags, fairness, pulses, sanitized journal + FTS recall, observations, three skills with propose-then-confirm + verification replay + self-adjustment, gitignore privacy. Report any gap to the user before declaring done.

- [ ] **Step 5: Commit any stragglers**

```bash
git add -A && git status   # review, then
git commit -m "chore: final verification pass"
```
