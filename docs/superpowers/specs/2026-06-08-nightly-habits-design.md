# Nightly Habits — design

**Date:** 2026-06-08
**Status:** approved, pending implementation plan

## Problem

The family wants to track a domain they intend to do *every single night*
— the first being **reviewing their spending** — and have the nightly
check-in (a) ritualistically ask about it every night and (b) flag neglect
when any night is missed, the same way laundry/chores neglect is surfaced.

No existing mechanism fits: the "daily-dose" flag is specific to personal
time, chores track a *learned* cadence (not "every night"), and the journal
is freeform with no miss-tracking.

## Goals

- A reusable mechanism for household **nightly habits** (not spending-only —
  the family may add more, e.g. meds, a 10-minute tidy).
- Household-level: one yes/no per night per habit (not per-adult).
- Surface every active habit in the nightly check-in report every night so
  it always gets asked.
- Auto-flag missed nights with a **current miss-streak + total missed since
  the habit started** (mirrors existing chore/drought flags).
- Full parity with the rest of the system: source-flagged writes, event log,
  `fam undo`, and `fam check` replay.

## Non-goals

- Per-adult tracking (explicitly chosen household-level).
- Weekly-planning integration — this is a daily-habit check, never a week
  entry.
- Backfilling history before a habit's creation date.

## Data model

Two new tables added to `famlib/db.py` `SCHEMA`:

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

Rationale:
- **Registry table (`daily_habits`)** is required so a habit with *zero*
  logs can still be flagged as missed — "should have happened" cannot be
  inferred from logs alone.
- **`daily_log`**: a row's *presence* means the habit was done that night.
  `UNIQUE(habit_id, date)` makes nightly logging idempotent (re-logging the
  same night is a no-op / note update, never a duplicate). No `status`
  column needed — absence of a row = a miss.
- Both table names are added to `famlib/events.py` `TABLES` so
  `snapshot` / `record` / `undo` / `check` operate on them like every other
  entity.

## Module: `famlib/daily.py`

Functions follow the existing module convention `(con, source, ...)` →
write + `events.record` with snapshots.

- `add_habit(con, source, name, today)` — insert into `daily_habits`
  (`sanitize.guard(name)` first); record an `add` event. Error if a habit of
  that name already exists.
- `log(con, source, name, date, note=None)` — resolve active habit by name;
  insert `daily_log` for `date` (validated via `dates.parse`). Idempotent on
  (habit, date): if a row exists, update its note rather than duplicating.
  Record the event.
- `retire_habit(con, source, name)` — set `status='retired'`; record event.
- `list_habits(con)` — list rows (for `fam daily list`).
- `neglect(con, today)` — for each **active** habit, compute:
  - `logged_today` — bool, a `daily_log` row exists for `today`.
  - `miss_streak` — consecutive missed nights ending *yesterday*
    (`today - 1`), walking backward while the date `>= created`. Tonight is
    not counted; the night isn't over at check-in time.
  - `total_missed` — count of dates in `[created, today)` with no log.
  - `elapsed` — count of nights in `[created, today)` (the denominator the
    report renders `total_missed` against).
  - `since` — the `created` date (acts as the horizon; a habit created today
    shows zero misses).
  Returns a list of dicts: `{name, logged_today, miss_streak, total_missed,
  elapsed, since}`.

## CLI: `fam daily`

Wired in `famlib/cli.py` alongside the other subparsers, honoring `--source`.

```
fam --source nightly daily add  "spending review"
fam --source nightly daily log  "spending review" [--date YYYY-MM-DD] [--note "..."]
fam daily list
fam --source nightly daily retire "spending review"
```

`add`/`log`/`retire` print a `WROTE ...` echo line (or equivalent); `list`
prints JSON rows like the other `list` subcommands.

## Report integration: `reports.checkin`

A new **NIGHTLY HABITS** section, placed immediately after the existing
`NEGLECT FLAGS` section (both are cadence-neglect trackers). Built from
`daily.neglect(con, today)`, one line per active habit:

- logged tonight → `spending review — ✓ logged tonight`
- not yet, no prior misses → `spending review — not yet logged tonight`
- not yet, with misses →
  `spending review — not yet tonight; MISSED 3 nights running (5 of 12 nights since 2026-06-08)`

Uses the shared `_section` helper so the `(n of n shown)` / `(none)`
formatting matches every other section. `reports.horizon` is left unchanged
(this is a nightly concern).

## Testing — `tests/test_daily.py`

Following the existing test style (`FAM_HOME` temp DB, direct module calls):

- `add_habit` creates a row and an event; duplicate name errors.
- `log` inserts a row; re-logging the same night is idempotent (no duplicate,
  note updates).
- `neglect` math:
  - habit created today, logged today → `logged_today=True`, streak 0, total 0.
  - habit created today, not logged → not flagged as a miss (horizon grace).
  - habit with a gap → correct `miss_streak` and `total_missed`.
- `events.undo` reverses a `log` (one event) and an `add`.
- A `reports` test asserting the NIGHTLY HABITS section renders each of the
  three line states.

## Follow-ups (separate, each with explicit sign-off)

1. **SKILL.md flow** — add a bullet to the check-in closing checklist:
   "nightly-habit logging (see NIGHTLY HABITS section)". Behavior change to
   the check-in skill → show diff → apply on confirm → commit.
2. **Tonight's data** — once shipped: `daily add "spending review"` then
   `daily log "spending review"` for 2026-06-08 (source `nightly`) = the
   first night of the streak.
