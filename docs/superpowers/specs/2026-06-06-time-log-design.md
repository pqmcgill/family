# Time log: ad-hoc personal & togetherness tracking — design

**Date:** 2026-06-06
**Status:** approved
**Origin:** founding-charter build-items (ritual.md): partial vs. full
personal time, daily small-dose tracking, togetherness drought flags.

## Problem

Personal time is tracked only through planned week entries
(`week_entries.kind='personal'`), so ad-hoc restorative moments — the
way this family actually lives the domain — are invisible to drought
detection. There is no togetherness concept at all, and no
partial/full distinction. The charter defines neglect thresholds the
code cannot currently measure:

- full personal reset ≥ 1×/week per adult (code has this, planned-only)
- small partial doses ~daily per adult (missing)
- couple time: >30 days without = too long (missing)
- family time: <2 moments per trailing 7 days = slipping (missing)

## Decision

New `time_log` table recording restorative time that *happened*
(planning stays in week entries; happening lives here). Chosen over
extending `week_entries` (would require a CHECK-constraint table
rebuild on a live DB and clutters the plan view with ad-hoc rows) and
over journal-text inference (fragile, unqueryable).

## Data model

```sql
CREATE TABLE IF NOT EXISTS time_log(
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('personal','couple','family')),
  level TEXT CHECK(level IN ('partial','full')),   -- personal only
  person_id INTEGER REFERENCES people(id),          -- personal only
  note TEXT
);
```

Appended to `db.SCHEMA` (CREATE IF NOT EXISTS — no migration).
Code-level validation (style of `standing.py`):

- `personal` requires an adult alias and a level
- `couple`/`family` must have neither person nor level
- notes pass `sanitize.guard` (real-name guard)
- all writes through `events.record` → `fam undo` works

## Module: `famlib/time_log.py`

- `add(con, source, kind, who=None, level=None, date=None, note=None)`
  → inserted row dict (CLI echoes `WROTE time_log #N`)
- `recent(con, today, days=14)` → list of dicts, newest first

## CLI surface (`famlib/cli.py`)

```
fam time log personal <alias> [--level partial|full] [--date YYYY-MM-DD] [--note "..."]
fam time log couple   [--date ...] [--note ...]
fam time log family   [--date ...] [--note ...]
fam time list [--days N]          # default 14
```

`--level` defaults to `partial`: undercounting full resets errs toward
flagging, the safe direction for an accountability system. `--date`
defaults to today.

## Drought logic (`famlib/reports.py`)

Constants: `PERSONAL_DROUGHT_DAYS = 7` (existing),
`DOSE_STREAK_DAYS = 2`, `COUPLE_DROUGHT_DAYS = 30`,
`FAMILY_WEEKLY_TARGET = 2`, `FAMILY_WINDOW_DAYS = 7`.

| Flag | Rule | Source |
|---|---|---|
| Full-reset drought (existing, extended) | >7 days since last full personal | union of done personal week entries and `time_log` personal `full`; take max date |
| Dose streak (new) | ≥2 consecutive days with no personal time of any kind/level | union of both sources |
| Couple drought (new) | >30 days since last couple moment | `time_log` couple |
| Family slipping (new) | <2 family moments in trailing 7 days | `time_log` family |

A planned personal week entry marked done counts as **full**. If a
planned block turned out partial, log a partial instead of marking the
entry done.

Grace periods follow the existing `personal_droughts` pattern: an
adult/household with no record is flagged only once the observation
horizon (earliest week start, or earliest time_log date if older) is
older than the flag's own window. Day one produces no wall of
warnings; the family flag additionally needs the horizon to clear its
7-day window.

## Report changes

- `checkin`: dose-streak lines join PERSONAL TIME DROUGHT; new
  TOGETHERNESS section (couple + family flags)
- `fair`: per-adult ad-hoc full/partial counts join the personal-blocks line
- `horizon`: new "TIME LOG (last 14 days)" section

## Testing

TDD. New `tests/test_time_log.py`: module add/recent, validation
errors (kid alias, level on couple, missing level default), CLI echo,
undo reversal. Extend `tests/test_reports.py`: boundary days (exactly
7 / 2 / 30), trailing-window edges, grace-period behavior, union-of-
sources correctness (planned-only, ad-hoc-only, both).

## Out of scope

- Levels on week entries
- Per-kid personal tracking
- Backfill tooling beyond `--date`
- Charter (ritual.md) build-items update ships separately with user
  sign-off after implementation
