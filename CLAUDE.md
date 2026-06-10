# family2 — guidance for Claude sessions

Family stress-management system. CLI is `bin/fam`, data in `data/family.db`,
library in `famlib/`. `ritual.md` is the family charter (gitignored — read it
for context, never commit it or copy personal details into tracked files).

## Answering "what's on today / what's todo"

Run `fam today`. It is the canonical, closed-world answer: session gaps,
WINS (positive momentum — lead with these), the week rollup line,
TODAY'S TARGETS (week entries whose `day` field is today), BEHIND PLAN
(assigned day passed, still pending), NO DAY ASSIGNED (pending,
unscheduled — nothing can hide), today's calendar, due/overdue todos,
and nightly habits. Pending entries show a pipeline tag like
`[dry since <date>]` when mid-stage.

For wider views: `fam checkin` (the nightly report — superset of today
plus neglect, pulses, droughts), `fam horizon` (everything open at any
distance, including a WEEK PLAN PENDING section), `fam journal list
--days N` (session narratives).

Day assignments live on week entries (`day` column, validated mon..sun);
set or move with `fam week day <id> <day>`. The "family day" rolls over
at 04:00 — a check-in just after midnight still counts as the prior
night.

## Other command map

- `fam todo list` — open one-off todos
- `fam cal list` — calendar items
- `fam chore list` — chore memory (last-done dates, cadence)
- `fam week done/skip <id>` — mark week-plan items (done cascades to a
  linked todo)
- `fam week day <id> <mon..sun>` — set/move an entry's day assignment
- `fam week note <id> "<text>"` — free-text context on an entry
- `fam week add ... [--day <d>] [--todo <id>]` — add entry, optionally
  linked to an open todo so the pair can't drift apart
- `fam week link <eid> <tid>` — link an existing entry to an open todo
- `fam week stage <id> <wash|dry|fold>` — track a multi-step entry
  mid-pipeline; put away = `fam week done`. Stalled stages (2+ days)
  become neglect flags
- `fam week new` — drafts next week; REFUSES while any earlier week has
  pending entries (disposition each first: done or skip)
- `fam journal list [--days N]` — read journal entries (full text)
- `fam check` — verify event log replays to current state
- `fam recall` — search past journal/observations
- `fam --source <manual|nightly|weekly|transcript|capture>` — set
  provenance when writing during a skill session

## Skills

- `/checkin` — nightly review (chores, todos, pulses, habits)
- `/weekly` — Sunday planning sweep; builds next week's plan
- `/capture` — quick mid-day notes outside a session
- `/setup` — found or amend the charter in ritual.md

## Conventions

- **Aliases only, by construction.** People exist as aliases (P1, K1,
  Grammy, ...) everywhere — db, reports, journals, tracked files. Real
  names never enter the system at all; who-is-who lives as relationship
  labels in ritual.md's People section (gitignored). Mentioned person
  doesn't resolve via `fam person list` + ritual.md? Stop and ask, then
  `fam person add`.
- Tests live in `tests/`; run with `pytest`.
