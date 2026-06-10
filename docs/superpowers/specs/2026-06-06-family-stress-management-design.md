# Family Stress Management System — Design

**Date:** 2026-06-06
**Status:** Approved pending user review

## Purpose

A local-first, conversational system used through Claude Code by two parents (aliased here as P1 and P2; P1 drives the sessions) to manage three domains of day-to-day stress:

1. Keeping the house clean
2. Keeping the to-do list and calendar organized
3. Managing each person's personal time

The system **facilitates the couple doing the work themselves** — it never does the work for them. It is stateful, accurate, and entirely local. The primary touchpoints are a **nightly check-in** and a **weekly review/planning session**. P1 drives the sessions; inputs are often raw speech-to-text transcripts of conversations between the couple, which the system parses for state changes.

## Core Principles

1. **Local-first.** All data lives in this project directory. No external services, no calendar sync, no cloud.
2. **Accuracy by construction.** The model never composes queries and never recalls state from memory. All reads and writes go through fixed CLI commands whose output is exhaustive and counted. The model's job is conversation and judgment; the database's job is memory.
3. **Flexible, not rigid.** Established recurring things (laundry groups, kids' classes) carry into each week automatically as standing items — but everything stays editable in conversation, and nothing is locked. Variable things (personal time, one-off chores) are planned fresh each week. The check-in ritual starts loose and converges through use. Rigidity is a failure mode; so is reinventing the week every time.
4. **Propose, then confirm.** Nothing extracted from conversation or transcripts is written until the user confirms it. Ambiguity becomes a question, never a guess.
5. **Nothing is ever lost.** Append-only event log; items are completed/dropped/deferred, never deleted. Far-future items are re-enumerated by code every week until resolved.
6. **Facts vs. inference, clearly separated.** Deterministic CLI output is the facts layer. Model-drawn insights are generated fresh at conversation time from complete data, visibly labeled as observations, and not persisted unless explicitly saved.
7. **Privacy by construction.** Real names are never written anywhere — not even the local database. All input (including transcripts) passes through a name-sanitization filter before any write. Personal data is gitignored; only general skill and system code is publishable.
8. **The system adapts itself.** Feedback about how the system works ("this isn't working how we thought") is first-class in any session: the skill proposes an edit to its own instructions or the ritual, shows the change, and applies it on confirmation.

## Architecture

```
family2/
├── .claude/skills/
│   ├── checkin/SKILL.md      # nightly session
│   ├── weekly/SKILL.md       # weekly review + planning
│   └── capture/SKILL.md      # ad-hoc quick capture
├── bin/fam                   # Python 3 CLI, stdlib only (sqlite3, argparse)
├── data/                     # GITIGNORED
│   ├── family.db             # SQLite source of truth
│   └── backups/              # timestamped copies, one per session
├── private/                  # GITIGNORED
│   └── names.txt             # real-name → alias map, used at parse time only
├── ritual.md                 # the evolving check-in structure (editable; GITIGNORED)
└── docs/superpowers/specs/   # design docs (alias-only, publishable)
```

- **SQLite** (`data/family.db`) is the single source of truth. Zero installs on macOS; FTS5 available for full-text search.
- **`bin/fam`** is a zero-dependency Python CLI wrapping all reads and writes. Claude never touches the database directly and never hand-edits data files.
- **Skills** are thin conversational layers over the CLI.

## The Accuracy Contract

### Writes

- Every state change is one CLI call (e.g., `fam todo add`, `fam chore done`, `fam pulse log`).
- Each write appends to an immutable event log **and** updates current-state tables in a single transaction.
- Every write echoes back the full record written (with id); the skill compares the echo against intent.
- `fam undo` reverses recent writes by appending compensating events — history stays intact.
- Validation at the boundary: malformed dates, duplicate chore names, etc. produce loud, specific errors. Exception: unknown person names are not errors — see People.

### Reads (canonical commands — the only way skills learn state)

- **`fam checkin`** — opens every nightly session. Prints everything active: current week plan and progress, all open to-dos, calendar items in the near window (next 14 days), neglect flags, this week's pulses. Every section carries an explicit count (`OPEN TODOS (14 of 14 shown)`) so truncation is impossible and omission is detectable.
- **`fam horizon`** — the anti-forgetting command. Lists **every** dated item from now to forever (with days-until) and **every** undated open item regardless of age. Runs automatically in every weekly review, so far-future items physically cannot fall off the radar.
- **`fam recall <term>`** — full-history search across structured data and journal text (FTS5).
- **`fam report`** — human-readable markdown summary of current state, generated on demand.
- **`fam check`** — integrity verification: replays the event log and confirms it matches current state.

- **Personal-time drought flags** — adults whose last completed personal block exceeds 7 days appear unprompted in checkin and fair output, with the same loudness as chore neglect.

### Verification loop

At the end of each session, the skill replays what it captured against the CLI's echo of what was actually written, and the user confirms. Mismatches are corrected on the spot via `fam undo` + re-entry.

## Data Model

### Entities

1. **People** — an open registry, not a fixed pair. Fields: **canonical alias** (the only identifier ever stored — never a real name), **role** (`adult` / `kid` / `other`), and **reference patterns** (nicknames and relational terms like "babe" or "grandma" that resolve to this person at parse time). The two adults are the primary users. Kids (Kid 1 and Kid 2) and others (family members, etc.) can own or be the subject of items. Role determines participation: pulses, fairness, and personal-time tracking apply to adults only.
   - **Name sanitization:** real names and their mappings to aliases live only in gitignored `private/names.txt`. Every input — conversation extracts and transcripts alike — is filtered through this map *before* any write, so a real name slipping into conversation never reaches the database or journal.
   - **Unknown person handling:** a new name in conversation/transcript triggers a proposal to add the person — the user picks an alias and role, the real name goes into `private/names.txt`, and the person is created via `fam person add` under the alias only. Never a hard error. Ambiguous references ("mom called") become clarifying questions.
2. **To-dos** — title, owner (person), optional date, status (`open` / `done` / `dropped` / `deferred`). Deferral count is tracked and feeds the inference layer.
3. **Calendar items** — local-only events/commitments with dates. No external calendar integration; the couple is the source of truth.
4. **Standing items** — established recurring commitments that flow into every week's plan automatically:
   - **Recurring chores**, possibly grouped (laundry → parents' clothes, Kid 1's clothes, Kid 2's bedding, towels), each with an owner and rough weekly expectation.
   - **Fixed weekly commitments** (Kid 1's swim class, Tuesday 4pm) that appear on the calendar view each week.
   Standing items are created, modified, paused, or retired at any time through conversation — they're remembered defaults, not locked schedules.
5. **Week plans** — created at each weekly review: the system pre-fills a draft from standing items ("here's what's standing — anything different this week?"), then the conversation adjusts it and adds the variable layer: personal-time blocks, one-off chores, anything specific to that week. Each entry has an owner and a status updated at nightly check-ins. Skipping or modifying a standing item for one week doesn't change the standing item itself.
6. **Chore memory** — one record per distinct chore ever planned (laundry groups, bedding, groceries...): last-done date and rough comfortable cadence. Powers neglect flags ("Kid 2's bedding: 24 days since last done, usually ~14") and informs weekly planning. Explicitly **not** a schedule.
7. **Pulses** — nightly stress/energy rating (1–10, where 10 is great + optional note) per adult. Powers trends and fairness review.
8. **Journal** — raw material of every session: sanitized-verbatim transcripts (real names replaced with aliases, everything else untouched) and/or a conversational summary of live dialogue, tied to session date and type (`nightly` / `weekly` / `capture`). Structured data is extracted from the journal; the journal itself is preserved untouched. Indexed with FTS5 from day one. Embeddings-based RAG is explicitly out of scope for this iteration; the captured data enables it later.
9. **Observations** — saved insights. The inference layer is ephemeral by default; when the user says an insight is worth keeping, it is persisted here and resurfaces in future check-ins as a fact.

### Infrastructure tables

- **Events** — append-only log of every change: timestamp, entity, action, payload, source (`nightly` / `weekly` / `transcript` / `capture`).
- FTS5 virtual tables over journal text (and to-do/observation titles) for `fam recall`.

## The Inference Layer

On top of the deterministic facts, the model draws insights at conversation time: deferral patterns, pulse trends correlated with personal time, chores that repeatedly slip, fairness imbalances. Rules:

- Insights are always generated from complete CLI output, never from conversational memory.
- Insights are visibly distinct from facts in dialogue ("the database says" vs. "I notice").
- Insights are not persisted unless the user asks; then they become observations.

## Sessions (Skills)

### `/checkin` — nightly

1. Back up the database; run `fam checkin`.
2. Open with what most needs attention (per the facts), then follow the natural flow of conversation. Ensure nothing is skipped: week-plan progress, new items, calendar look-ahead, pulse for each adult.
3. Accept pasted transcripts at any point: parse, propose extracted changes as a batch ("From your conversation I'm capturing: ..."), write only on confirmation.
4. Close with the verification replay.
5. Structure is guided by `ritual.md`, which starts loose. When patterns settle through use, the user can ask to update the ritual; the skill edits `ritual.md`. The ritual emerges; it is not imposed.

### `/weekly` — review + planning

1. Back up; run `fam horizon` (full sweep — every open item in the system, however far out).
2. Review: neglect flags from chore memory, fairness check on personal-time actuals between the adults (trailing weeks), pulse trends, deferral patterns.
3. Plan next week: the system presents a draft pre-filled from standing items, the conversation adjusts it (skip/shift/modify for this week) and adds the variable layer — personal-time blocks, one-off chores. Standing items themselves can be added, changed, or retired here too.
4. Create the week plan via CLI; verification replay.

### `/capture` — ad-hoc

Paste a transcript or quick note any time; extract, confirm, write, exit. No ritual. Prevents "I'll remember it tonight" losses.

## Privacy & Publication

- **No real names anywhere in stored data** — database, journal, ritual, and docs use aliases only. The real-name → alias map exists solely in gitignored `private/names.txt` and is consulted at parse time.
- **Sanitization is a pre-write step**, not a cleanup: the skills filter every extract and transcript through the name map before calling any write command. The CLI additionally refuses writes containing a name found in the map (defense in depth).
- **`.gitignore` from day one:** `data/`, `private/`, `ritual.md`, and any session artifacts. If the project is published on GitHub, only the general layer is public: skills, CLI code, tests, and alias-only design docs.
- **Skill files stay general.** Personal specifics (your actual chore names, family details, ritual preferences) accumulate in `ritual.md` and the database — both gitignored — never in `.claude/skills/`.

## Self-Adjustment

Feedback about the system itself is first-class in any session. When the users say something isn't working — the flow, a behavior, a missing capability — the active skill:

1. Identifies whether the change belongs in `ritual.md` (personal routine/preferences) or a `SKILL.md` (general behavior).
2. Proposes the concrete edit and shows the diff.
3. Applies on confirmation and commits (skill changes to git; ritual changes stay local).

This is the same mechanism by which the check-in ritual converges over time.

## Error Handling

- CLI validates all input at the boundary; errors are loud and specific.
- Write echoes enable immediate mismatch detection.
- Transcript parsing is propose-then-confirm; ambiguity becomes questions.
- `fam undo` provides recovery via compensating events.
- Timestamped database backup before every session (kilobytes-scale for years).
- `fam check` verifies event-log/state consistency on demand.

## Testing

- **CLI:** stdlib `unittest` suite covering every command, the event-log → state replay invariant, counts-always-shown, undo, FTS search, and unknown-person flow.
- **Skills:** authored and verified per the `writing-skills` methodology — subagents run simulated check-ins (including a messy fake transcript) to confirm propose-then-confirm and verification-replay behaviors hold.
- **Integrity:** `fam check` runnable anytime.

## Out of Scope (this iteration)

- External calendar integration (read or write).
- Embeddings/semantic RAG over journals (data is captured to enable it later).
- Notifications, scheduling automation, or anything that does the work for the couple.
- Multi-machine sync.

## Open Decisions Resolved During Brainstorming

| Question | Decision |
|---|---|
| Usage model | P1 drives; inputs often transcripts of couple's conversations |
| Calendar | Local-only |
| Personal time | All four: protected blocks, fairness, pulse, week planning |
| House cleaning | Weekly chore lists from planning sessions + freshness/neglect memory; no rigid recurrence |
| Recurring structure | Standing items (laundry groups, fixed kid classes) pre-fill each week's draft plan; editable per-week without changing the standing default |
| Check-in structure | Flexible at onset; ritual emerges through use (`ritual.md`) |
| Touchpoints | Nightly + weekly review (plus lightweight `/capture`) |
| Persistence | SQLite + zero-dependency Python CLI (Approach A) |
| People | Open registry with roles and aliases; unknown names proposed, never errors |
| Privacy | Aliases only in all stored data; real-name map gitignored; data/private/ritual gitignored for publication |
| Adaptability | Skills and ritual self-adjust through in-session feedback, diff shown, confirm to apply |
