# Nightly Habits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable household "nightly habit" mechanism (first habit: spending review) that the nightly check-in surfaces every night and auto-flags with a miss-streak when a night is skipped.

**Architecture:** Two new tables (`daily_habits` registry + `daily_log`), a new `famlib/daily.py` module following the existing `(con, source, ...)` + `events.record` convention, a `fam daily` CLI subcommand, and a NIGHTLY HABITS section in `reports.checkin`. All writes are event-logged so `fam undo` and `fam check` work unchanged.

**Tech Stack:** Python 3 stdlib, sqlite3, unittest/pytest. No new dependencies.

---

## File Structure

- **Modify** `famlib/db.py` — add two tables to `SCHEMA`.
- **Modify** `famlib/events.py` — add the two table names to the `TABLES` allowlist.
- **Create** `famlib/daily.py` — habit registry + logging + neglect math.
- **Modify** `famlib/cli.py` — import `daily`, wire the `fam daily` subcommand.
- **Modify** `famlib/reports.py` — import `daily`, add `_habit_lines` + NIGHTLY HABITS section in `checkin`.
- **Create** `tests/test_daily.py` — module + neglect-math + undo tests.
- **Modify** `tests/test_reports.py` — assert the NIGHTLY HABITS section renders.

Run all tests any time with: `python3 -m pytest -q`

---

### Task 1: Schema + events allowlist

**Files:**
- Modify: `famlib/db.py` (inside the `SCHEMA` string, before the closing `"""`)
- Modify: `famlib/events.py:8-9` (the `TABLES` list)
- Test: `tests/test_daily.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_daily.py`:

```python
from tests.base import FamTest
from famlib import daily, events


class TestDaily(FamTest):
    def test_schema_tables_exist(self):
        names = {r["name"] for r in self.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("daily_habits", names)
        self.assertIn("daily_log", names)

    def test_tables_in_events_allowlist(self):
        self.assertIn("daily_habits", events.TABLES)
        self.assertIn("daily_log", events.TABLES)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_daily.py -v`
Expected: FAIL — `daily_habits` not in tables / not in `events.TABLES`. (The `import daily` line also fails until Task 2; that is expected and is fixed there — for this task you may temporarily drop `daily` from the import to see these two tests fail, then restore it in Task 2. Simpler: run only after Task 2 if the import blocks collection. If so, proceed knowing the schema/allowlist edits below are what these assertions cover.)

- [ ] **Step 3: Add the two tables to `SCHEMA`**

In `famlib/db.py`, immediately before the closing `"""` of `SCHEMA` (after the `events` table definition), add:

```sql
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
```

- [ ] **Step 4: Add the table names to the allowlist**

In `famlib/events.py`, change the `TABLES` list (lines 8-9) to include the two new tables:

```python
TABLES = ["people", "todos", "calendar", "standing", "weeks", "week_entries",
          "chore_memory", "pulses", "journal", "observations", "time_log",
          "daily_habits", "daily_log"]
```

- [ ] **Step 5: Run the schema/allowlist tests**

Run: `python3 -m pytest tests/test_daily.py -k "schema or allowlist" -v`
Expected: PASS (2 tests). If collection fails on `import daily`, complete Task 2 first, then re-run.

- [ ] **Step 6: Commit**

```bash
git add famlib/db.py famlib/events.py tests/test_daily.py
git commit -m "feat(daily): nightly-habit tables + events allowlist"
```

---

### Task 2: `daily.add_habit` and `list_habits`

**Files:**
- Create: `famlib/daily.py`
- Test: `tests/test_daily.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_daily.py` (inside `class TestDaily`):

```python
    def test_add_habit_creates_row_and_event(self):
        row = daily.add_habit(self.con, "manual", "spending review",
                              today="2026-06-08")
        self.assertEqual(row["name"], "spending review")
        self.assertEqual(row["status"], "active")
        self.assertEqual(row["created"], "2026-06-08")
        ev = self.con.execute(
            "SELECT * FROM events WHERE entity='daily_habits'").fetchone()
        self.assertEqual(ev["action"], "add")

    def test_add_duplicate_name_refused(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        with self.assertRaises(SystemExit):
            daily.add_habit(self.con, "manual", "spending review",
                            today="2026-06-09")

    def test_add_empty_name_refused(self):
        with self.assertRaises(SystemExit):
            daily.add_habit(self.con, "manual", "   ", today="2026-06-08")

    def test_list_habits(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        names = [h["name"] for h in daily.list_habits(self.con)]
        self.assertEqual(names, ["spending review"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_daily.py -k "add or list_habits" -v`
Expected: FAIL — `ModuleNotFoundError: famlib.daily` or `AttributeError`.

- [ ] **Step 3: Create `famlib/daily.py`**

```python
from famlib import dates, events, sanitize


def add_habit(con, source, name, today=None):
    if not name or not name.strip():
        raise SystemExit("habit name must not be empty")
    sanitize.guard(name)
    if con.execute("SELECT 1 FROM daily_habits WHERE name=?",
                   (name,)).fetchone():
        raise SystemExit("habit %r already exists" % name)
    created = today or dates.today()
    dates.parse(created)
    with con:
        cur = con.execute(
            "INSERT INTO daily_habits(name, created) VALUES (?,?)",
            (name, created))
        row = events.snapshot(con, "daily_habits", cur.lastrowid)
        events.record(con, source, "daily_habits", cur.lastrowid, "add",
                      None, row)
    return row


def list_habits(con):
    return [dict(r) for r in con.execute(
        "SELECT * FROM daily_habits ORDER BY id")]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_daily.py -k "add or list_habits or schema or allowlist" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add famlib/daily.py tests/test_daily.py
git commit -m "feat(daily): add_habit + list_habits"
```

---

### Task 3: `daily.log` (idempotent per night)

**Files:**
- Modify: `famlib/daily.py`
- Test: `tests/test_daily.py`

- [ ] **Step 1: Write the failing test**

Append to `class TestDaily`:

```python
    def test_log_inserts_row_and_event(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        row = daily.log(self.con, "nightly", "spending review",
                        date="2026-06-08", note="reviewed")
        self.assertEqual(row["date"], "2026-06-08")
        self.assertEqual(row["note"], "reviewed")
        n = self.con.execute("SELECT COUNT(*) AS n FROM daily_log").fetchone()
        self.assertEqual(n["n"], 1)
        ev = self.con.execute(
            "SELECT * FROM events WHERE entity='daily_log'").fetchone()
        self.assertEqual(ev["action"], "log")

    def test_log_idempotent_per_night(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        daily.log(self.con, "nightly", "spending review", date="2026-06-08")
        daily.log(self.con, "nightly", "spending review", date="2026-06-08",
                  note="updated")
        rows = self.con.execute("SELECT * FROM daily_log").fetchall()
        self.assertEqual(len(rows), 1)            # no duplicate
        self.assertEqual(rows[0]["note"], "updated")  # note updated

    def test_log_unknown_habit_refused(self):
        with self.assertRaises(SystemExit):
            daily.log(self.con, "nightly", "ghost", date="2026-06-08")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_daily.py -k "log" -v`
Expected: FAIL — `AttributeError: module 'famlib.daily' has no attribute 'log'`.

- [ ] **Step 3: Add `log` to `famlib/daily.py`**

Append to `famlib/daily.py`:

```python
def log(con, source, name, date=None, note=None):
    h = con.execute(
        "SELECT * FROM daily_habits WHERE name=? AND status='active'",
        (name,)).fetchone()
    if h is None:
        raise SystemExit("no active habit named %r" % name)
    d = date or dates.today()
    dates.parse(d)
    existing = con.execute(
        "SELECT * FROM daily_log WHERE habit_id=? AND date=?",
        (h["id"], d)).fetchone()
    with con:
        if existing is None:
            cur = con.execute(
                "INSERT INTO daily_log(habit_id, date, note) VALUES (?,?,?)",
                (h["id"], d, note))
            row = events.snapshot(con, "daily_log", cur.lastrowid)
            events.record(con, source, "daily_log", cur.lastrowid, "log",
                          None, row)
        else:
            before = dict(existing)
            con.execute("UPDATE daily_log SET note=? WHERE id=?",
                        (note, existing["id"]))
            row = events.snapshot(con, "daily_log", existing["id"])
            events.record(con, source, "daily_log", existing["id"], "log",
                          before, row)
    return row
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_daily.py -k "log" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add famlib/daily.py tests/test_daily.py
git commit -m "feat(daily): idempotent nightly log"
```

---

### Task 4: `daily.retire_habit`

**Files:**
- Modify: `famlib/daily.py`
- Test: `tests/test_daily.py`

- [ ] **Step 1: Write the failing test**

Append to `class TestDaily`:

```python
    def test_retire_habit(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        row = daily.retire_habit(self.con, "manual", "spending review")
        self.assertEqual(row["status"], "retired")

    def test_retire_unknown_refused(self):
        with self.assertRaises(SystemExit):
            daily.retire_habit(self.con, "manual", "ghost")

    def test_retire_already_retired_refused(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        daily.retire_habit(self.con, "manual", "spending review")
        with self.assertRaises(SystemExit):
            daily.retire_habit(self.con, "manual", "spending review")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_daily.py -k "retire" -v`
Expected: FAIL — no attribute `retire_habit`.

- [ ] **Step 3: Add `retire_habit` to `famlib/daily.py`**

Append to `famlib/daily.py`:

```python
def retire_habit(con, source, name):
    before = con.execute(
        "SELECT * FROM daily_habits WHERE name=?", (name,)).fetchone()
    if before is None:
        raise SystemExit("no habit named %r" % name)
    if before["status"] == "retired":
        raise SystemExit("habit %r is already retired" % name)
    with con:
        con.execute("UPDATE daily_habits SET status='retired' WHERE id=?",
                    (before["id"],))
        after = events.snapshot(con, "daily_habits", before["id"])
        events.record(con, source, "daily_habits", before["id"], "retire",
                      dict(before), after)
    return after
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_daily.py -k "retire" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add famlib/daily.py tests/test_daily.py
git commit -m "feat(daily): retire_habit"
```

---

### Task 5: `daily.neglect` (streak + total + horizon grace)

**Files:**
- Modify: `famlib/daily.py`
- Test: `tests/test_daily.py`

- [ ] **Step 1: Write the failing test**

Append to `class TestDaily`:

```python
    def test_neglect_created_today_logged(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        daily.log(self.con, "nightly", "spending review", date="2026-06-08")
        f = daily.neglect(self.con, "2026-06-08")[0]
        self.assertTrue(f["logged_today"])
        self.assertEqual(f["miss_streak"], 0)
        self.assertEqual(f["total_missed"], 0)
        self.assertEqual(f["elapsed"], 0)

    def test_neglect_created_today_not_logged_has_grace(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        f = daily.neglect(self.con, "2026-06-08")[0]
        self.assertFalse(f["logged_today"])
        self.assertEqual(f["miss_streak"], 0)   # tonight isn't over; no misses
        self.assertEqual(f["total_missed"], 0)

    def test_neglect_counts_streak_and_total(self):
        # created 06-01; logged 06-02 and 06-05; today is 06-08
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-01")
        daily.log(self.con, "nightly", "spending review", date="2026-06-02")
        daily.log(self.con, "nightly", "spending review", date="2026-06-05")
        f = daily.neglect(self.con, "2026-06-08")[0]
        # elapsed nights = [06-01, 06-08) = 7 nights (01,02,03,04,05,06,07)
        self.assertEqual(f["elapsed"], 7)
        # logged: 02, 05 -> missed: 01,03,04,06,07 = 5
        self.assertEqual(f["total_missed"], 5)
        # streak ending yesterday (06-07): 07,06 missing -> 2
        self.assertEqual(f["miss_streak"], 2)
        self.assertFalse(f["logged_today"])

    def test_neglect_skips_retired(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-01")
        daily.retire_habit(self.con, "manual", "spending review")
        self.assertEqual(daily.neglect(self.con, "2026-06-08"), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_daily.py -k "neglect" -v`
Expected: FAIL — no attribute `neglect`.

- [ ] **Step 3: Add `neglect` to `famlib/daily.py`**

Append to `famlib/daily.py`:

```python
def neglect(con, today):
    """Per active habit: today's status, current miss-streak (consecutive
    missed nights ending yesterday — tonight isn't over yet), total missed
    nights since creation, and elapsed nights since creation. The creation
    date is the horizon, so a brand-new habit shows no phantom misses."""
    out = []
    for h in con.execute(
            "SELECT * FROM daily_habits WHERE status='active' ORDER BY id"):
        created = h["created"]
        logged = {r["date"] for r in con.execute(
            "SELECT date FROM daily_log WHERE habit_id=?", (h["id"],))}
        logged_today = today in logged
        # elapsed required nights: dates d with created <= d < today
        elapsed = 0
        total_missed = 0
        d = created
        while dates.days_until(d, today) > 0:   # d < today
            elapsed += 1
            if d not in logged:
                total_missed += 1
            d = dates.add_days(d, 1)
        # miss streak: consecutive missed nights walking back from yesterday
        miss_streak = 0
        d = dates.add_days(today, -1)
        while dates.days_until(created, d) >= 0:  # d >= created
            if d in logged:
                break
            miss_streak += 1
            d = dates.add_days(d, -1)
        out.append({"name": h["name"], "logged_today": logged_today,
                    "miss_streak": miss_streak, "total_missed": total_missed,
                    "elapsed": elapsed, "since": created})
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_daily.py -k "neglect" -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add famlib/daily.py tests/test_daily.py
git commit -m "feat(daily): neglect streak + total + horizon grace"
```

---

### Task 6: `events.undo` reverses daily writes

**Files:**
- Test: `tests/test_daily.py` (no production change expected — confirms Task 1 allowlist is sufficient)

- [ ] **Step 1: Write the failing test**

Append to `class TestDaily`:

```python
    def test_undo_reverses_log(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        daily.log(self.con, "nightly", "spending review", date="2026-06-08")
        events.undo(self.con, 1)
        n = self.con.execute("SELECT COUNT(*) AS n FROM daily_log").fetchone()
        self.assertEqual(n["n"], 0)

    def test_undo_reverses_add(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        events.undo(self.con, 1)
        n = self.con.execute(
            "SELECT COUNT(*) AS n FROM daily_habits").fetchone()
        self.assertEqual(n["n"], 0)

    def test_check_replays_clean(self):
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        daily.log(self.con, "nightly", "spending review", date="2026-06-08")
        self.assertEqual(events.check(self.con), [])  # no drift
```

- [ ] **Step 2: Run test to verify it passes (or fails)**

Run: `python3 -m pytest tests/test_daily.py -k "undo or check_replays" -v`
Expected: PASS — Task 1 already added both tables to `events.TABLES`, so `undo`/`check` work. If any FAIL, the allowlist edit in Task 1 is incomplete; fix `famlib/events.py` `TABLES` and re-run.

- [ ] **Step 3: Commit**

```bash
git add tests/test_daily.py
git commit -m "test(daily): undo + event-replay coverage"
```

---

### Task 7: CLI — `fam daily` subcommand

**Files:**
- Modify: `famlib/cli.py` (import on lines 7-9; subparser block near line 164 after the `obs` block; dispatch near line 324 after the `obs` dispatch)

- [ ] **Step 1: Add the import**

In `famlib/cli.py`, add `daily` to the famlib import (keep alphabetical-ish with the rest). Change:

```python
from famlib import (calendar_items, chores, dates, db, events, journal,
                    observations, people, pulses, reports, standing,
                    time_log, todos, weeks)
```

to:

```python
from famlib import (calendar_items, chores, daily, dates, db, events, journal,
                    observations, people, pulses, reports, standing,
                    time_log, todos, weeks)
```

- [ ] **Step 2: Add the subparser block**

In `famlib/cli.py`, immediately after the `obs` subparser block (the lines defining `op`, `oa`, `ox`, and `op.add_parser("list")`, ending near line 164) and before `a = p.parse_args(argv)`, add:

```python
    dp = sub.add_parser("daily").add_subparsers(dest="sub", required=True)
    dda = dp.add_parser("add")
    dda.add_argument("name")
    ddl = dp.add_parser("log")
    ddl.add_argument("name")
    ddl.add_argument("--date")
    ddl.add_argument("--note")
    ddr = dp.add_parser("retire")
    ddr.add_argument("name")
    dp.add_parser("list")
```

- [ ] **Step 3: Add the dispatch block**

In `famlib/cli.py`, immediately after the `elif a.cmd == "obs":` block (ending with its `for r in observations.list_active(con): print(...)`, near line 324) and before `return 0`, add:

```python
        elif a.cmd == "daily":
            if a.sub == "add":
                echo("daily_habits", daily.add_habit(con, src, a.name,
                                                     today=today))
            elif a.sub == "log":
                echo("daily_log", daily.log(con, src, a.name, date=a.date,
                                            note=a.note))
            elif a.sub == "retire":
                echo("daily_habits", daily.retire_habit(con, src, a.name))
            else:
                for r in daily.list_habits(con):
                    print(json.dumps(r, ensure_ascii=False))
```

- [ ] **Step 4: Manually verify the CLI end-to-end against a throwaway DB**

Run (uses a temp `FAM_HOME` so real data is untouched):

```bash
FAM_HOME=$(mktemp -d) sh -c '
  ./bin/fam --source nightly daily add "spending review" &&
  ./bin/fam --source nightly daily log "spending review" --note "reviewed" &&
  ./bin/fam daily list &&
  ./bin/fam check'
```

Expected: a `WROTE daily_habits #1` line, a `WROTE daily_log #1` line, one JSON habit row from `list`, and `OK — event log replays to current state` from `check`.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all tests pass (existing + new `tests/test_daily.py`).

- [ ] **Step 6: Commit**

```bash
git add famlib/cli.py
git commit -m "feat(daily): fam daily CLI subcommand"
```

---

### Task 8: Report — NIGHTLY HABITS section

**Files:**
- Modify: `famlib/reports.py` (import line 1-2; new `_habit_lines` helper; section inside `checkin` after the NEGLECT FLAGS block, ~line 221)
- Test: `tests/test_reports.py`

- [ ] **Step 1: Write the failing test**

Open `tests/test_reports.py`, look at the top for the existing import line and test-class pattern, and append a test to the existing test class (match the class name already in the file). Use this test body:

```python
    def test_checkin_shows_nightly_habits(self):
        from famlib import daily
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-08")
        # not logged tonight, no prior misses
        out = reports.checkin(self.con, "2026-06-08")
        self.assertIn("NIGHTLY HABITS", out)
        self.assertIn("spending review — not yet logged tonight", out)
        # logged tonight
        daily.log(self.con, "nightly", "spending review", date="2026-06-08")
        out = reports.checkin(self.con, "2026-06-08")
        self.assertIn("spending review — ✓ logged tonight", out)

    def test_checkin_flags_missed_habit_streak(self):
        from famlib import daily
        daily.add_habit(self.con, "manual", "spending review",
                        today="2026-06-01")
        daily.log(self.con, "nightly", "spending review", date="2026-06-02")
        out = reports.checkin(self.con, "2026-06-08")
        self.assertIn("MISSED", out)
        self.assertIn("nights since 2026-06-01", out)
```

Note: if `tests/test_reports.py` imports `reports` at module top, reuse that; do not re-import. If its test class needs a `reports` reference and already has one, drop the local imports accordingly. The `from famlib import daily` inside each test is safe regardless.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_reports.py -k "nightly_habits or missed_habit" -v`
Expected: FAIL — "NIGHTLY HABITS" not found in output.

- [ ] **Step 3: Add the import and helper to `famlib/reports.py`**

Change the import (lines 1-2) from:

```python
from famlib import (calendar_items, chores, dates, journal, observations,
                    people, pulses, standing, time_log, todos, weeks)
```

to:

```python
from famlib import (calendar_items, chores, daily, dates, journal,
                    observations, people, pulses, standing, time_log, todos,
                    weeks)
```

Then add this helper function above `def checkin(` (e.g. right after `_drought_lines`):

```python
def _habit_lines(flags):
    lines = []
    for f in flags:
        if f["logged_today"]:
            lines.append("%s — ✓ logged tonight" % f["name"])
        elif f["miss_streak"] == 0:
            lines.append("%s — not yet logged tonight" % f["name"])
        else:
            lines.append(
                "%s — not yet tonight; MISSED %d night%s running"
                " (%d of %d nights since %s)" % (
                    f["name"], f["miss_streak"],
                    "" if f["miss_streak"] == 1 else "s",
                    f["total_missed"], f["elapsed"], f["since"]))
    return lines
```

- [ ] **Step 4: Add the section to `checkin`**

In `famlib/reports.py`, inside `checkin`, immediately after the NEGLECT FLAGS section and its trailing `out.append("")` (the block ending around line 222, right before the `PERSONAL TIME DROUGHT` section), insert:

```python
    out += _section("NIGHTLY HABITS",
                    _habit_lines(daily.neglect(con, today)))
    out.append("")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_reports.py -k "nightly_habits or missed_habit" -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add famlib/reports.py tests/test_reports.py
git commit -m "feat(daily): NIGHTLY HABITS section in checkin report"
```

---

## Post-implementation (handled outside this plan, each with explicit user sign-off)

These are **not** code tasks for the executing agent — they are check-in actions the facilitator does after the feature ships:

1. **SKILL.md flow bullet** — propose adding "nightly-habit logging (see NIGHTLY HABITS section)" to the check-in closing checklist; show diff; on confirm, `git add .claude/skills && git commit`.
2. **Tonight's data (2026-06-08)** — `fam --source nightly daily add "spending review"` then `fam --source nightly daily log "spending review"` = first night of the streak.

---

## Self-Review

- **Spec coverage:** tables (T1) ✓; events allowlist + undo/check (T1, T6) ✓; `daily.py` add/log/retire/list/neglect (T2-T5) ✓; CLI (T7) ✓; report section with all three line states + miss flag (T8) ✓; tests (T1-T8) ✓; follow-ups (post-impl) ✓. No gaps.
- **Placeholder scan:** no TBD/TODO; every code step shows full code; every run step shows expected output.
- **Type/name consistency:** `add_habit`, `log`, `retire_habit`, `list_habits`, `neglect` used identically across module, CLI, and reports. `neglect` dict keys (`name`, `logged_today`, `miss_streak`, `total_missed`, `elapsed`, `since`) match between Task 5 and the `_habit_lines` consumer in Task 8. Table names `daily_habits`/`daily_log` consistent across schema, allowlist, module, CLI echo, and tests.
