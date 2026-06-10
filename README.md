# Family Check-in System

A local-first, code-driven system for two parents to manage household
stress through [Claude Code](https://claude.com/claude-code): chores,
to-dos, calendar, personal time, and the nightly/weekly rituals that
keep them honest. SQLite underneath, a small CLI in the middle,
conversational skills on top.

The system facilitates us doing the work — it never does the work for us.

This is the second iteration. The first ([family-v1](https://github.com/pqmcgill/family-v1))
was prompt-driven: YAML state files, markdown plans, and LLM agents that
re-derived everything each session. It taught us the core lesson this
version is built on: **completeness can't depend on a language model's
discipline.** Anything that must never fall through the cracks has to be
enforced by code and schema — the LLM is the conversational interface,
not the bookkeeper.

## Design principles

- **Closed-world accountability.** Every report is exhaustive and says
  so (`N of N shown`). Every item is either resolved, scheduled, or
  flagged — there is no state an item can reach where it silently stops
  appearing. `fam week new` literally refuses to draft a new week while
  the old one has undispositioned entries.
- **Code computes, the model converses.** Neglect thresholds, day
  targets, streaks, droughts, fairness — all deterministic queries, not
  LLM judgment. Skills read reports and talk with the family.
- **Celebrate wins, not just punish failures.** Reports open with a
  WINS section (habit streaks, chores on rhythm, plan progress) before
  any neglect flag.
- **Aliases by construction.** People exist only as aliases (P1, K1,
  Grammy). Real names never enter the system — db, files, or reports —
  so nothing it writes can leak them. Who-is-who lives as relationship
  labels in the gitignored `ritual.md`.
- **Append-only event log.** Every write is recorded with
  before/after snapshots: `fam undo` reverses anything, and `fam check`
  verifies the log replays exactly to current state.

## Setup

Requires Python ≥ 3.9 (stdlib only — no dependencies).

```bash
./bin/fam init                       # creates data/, ritual.md
git config core.hooksPath .githooks  # safety net: blocks private paths from commits
```

Add your people (aliases only — pick relationship names you'd say out loud):

```bash
./bin/fam person add P1 --role adult
./bin/fam person add P2 --role adult
./bin/fam person add K1 --role kid
```

Then open Claude Code here and run `/setup` to found your charter —
domains, standing chores, commitments, and what "neglect" means for
your family. It all lands in `ritual.md` (gitignored) and the database.

## Daily use

- `/checkin` — nightly check-in: what happened, what slipped, pulses
- `/weekly` — Sunday review + plan next week (day-by-day assignments)
- `/capture` — quick ad-hoc capture, any time

## The CLI

`./bin/fam --help` for everything. Highlights:

- `fam today` — the canonical "what's on today": session gaps, WINS,
  the week rollup, today's targets, behind-plan items, unscheduled
  items, calendar, due to-dos, habits. Closed-world: nothing can hide.
- `fam checkin` / `fam horizon` — the nightly report and the
  everything-open-at-any-distance report
- `fam week day <id> <mon..sun>` — day assignments; reports compute
  TODAY'S TARGETS and BEHIND PLAN from them
- `fam week stage <id> <wash|dry|fold>` — multi-step chores tracked
  mid-pipeline; a load stalled 2+ days becomes a neglect flag
- `fam week add ... --todo <id>` / `fam week link` — tie a week entry
  to an open todo so completing one resolves both
- `fam week new` — drafts next week from standing chores; refuses while
  any earlier week has pending entries (disposition each first)
- `fam time log personal|couple|family` — restorative-time log feeding
  the drought flags
- `fam journal list` / `fam recall <term>` — full-history reading and
  search (SQLite FTS5)
- `fam undo` / `fam check` / `fam backup` — event-log reversal,
  integrity replay, timestamped db copies
- `--source` is a global flag and goes before the subcommand:
  `fam --source nightly week done 3`

Late nights are handled: before 04:00 counts as the previous day, so a
half-past-midnight check-in lands on the night it describes.

## Privacy

- People are aliases everywhere; real names never enter the system, so
  no mapping file, no sanitization layer, nothing to misconfigure.
  The LLM can't leak what it never learns.
- `data/`, `private/`, and `ritual.md` are gitignored; the pre-commit
  hook refuses to stage them. Tracked files are only code, skills, and
  generic docs.
- Adapt it: this encodes one family's rituals. Fork it, run `/setup`,
  and reshape the domains to fit your life.

## Architecture

```
famlib/            zero-dependency Python (stdlib + SQLite + FTS5)
bin/fam            the only interface the skills use — deterministic
                   reads and writes; the model never recalls state
                   from memory
.claude/skills/    the conversational layer (setup/checkin/weekly/capture)
ritual.md          the family charter — gitignored, evolves with use
data/family.db     everything; append-only event log alongside
```

Tests: `python3 -m pytest tests/` (225 tests, written test-first).

## License

MIT — see [LICENSE](LICENSE).
