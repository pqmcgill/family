---
name: setup
description: Use when the family wants to establish or amend their domain charter — first-time founding setup, "redo our domains", "amend the charter", or onboarding a fresh household database.
---

# Founding Setup / Charter Amendment

A collaborative session where the adults define (or amend) the domain
layer: what areas of life this system manages, what machinery each
domain runs on, and what neglect means in each. The goal is setting
the stage, NEVER locking anything in — the charter is amendable by
re-running this skill anytime.

Same hard rules as the nightly check-in skill: read the "Hard rules"
and "Red flags" sections of `.claude/skills/checkin/SKILL.md` FIRST and
apply all of them identically (CLI only; read before you think; full
batch then confirm then write; never guess facts; aliases only; every
write carries `--source weekly`).

## Conversation discipline (setup-specific)

- **One topic at a time.** Never present a wall of questions. This is
  a conversation between partners that you facilitate — ask, listen,
  reflect back, move on.
- **Propose, don't impose.** You may offer the classic domains (house,
  to-dos/calendar, personal time, togetherness) as a starting point,
  clearly labeled as a starting point. Their domains are whatever they
  say they are.
- **Both voices.** This session is for BOTH adults. If only one is
  present, ask which decisions should wait for the other.

## Flow

1. Read state first: `./bin/fam backup`, `./bin/fam person list`,
   `./bin/fam standing list`, `./bin/fam --source weekly horizon`,
   read `ritual.md`.
   - Empty system → founding session (full flow below).
   - Existing system → amendment: present the current charter from
     ritual.md section by section and ask what's changed. Apply the
     same flow only to the parts being amended.
2. **Domains** — "What are the areas of life we want this system to
   help carry?" Capture each domain and, in one phrase, why it matters
   to them.
3. **People** — register everyone (aliases + roles + nickname
   patterns), and record who-is-who as relationships in a "People"
   section of ritual.md ("P1 — dad", "Grammy — P2's mother"). Real
   names never enter the system anywhere — aliases by construction.
4. **Machinery per domain** — for each domain, what are the moving
   parts? Recurring chores (with groupings), fixed commitments
   (day/time, pausable for seasons), backlog one-offs, anything
   tracked as to-dos. Write as standing items / todos as agreed.
5. **Neglect definitions** — for each domain: "how long is too long?"
   - Chore cadences → `fam chore cadence <name> <days>` (note: a chore
     enters chore memory after its first completion; declared cadences
     for not-yet-done chores go in the charter and get set at first
     completion).
   - Personal/together drought thresholds → these are code constants;
     record the agreed numbers in the charter and flag any that differ
     from current code as build-items.
6. **Long-term priorities** — "What do we keep meaning to protect or
   fix?" Each becomes an observation (`fam obs add`) so it resurfaces
   at every session.
7. **Ritual shape** — when do weeklies happen, what must every
   check-in cover, any house habits (e.g. nightly reset)?
8. **Write the charter** — update `ritual.md` with structured
   sections: `## Our domains`, `## What neglect means`,
   `## Scheduling context`, `## Preferences we've settled on`.
   Show the full diff before applying.
9. **Verification replay** — all WROTE echoes against what was agreed;
   confirm; fix with `fam undo` if wrong. Close by reminding them the
   charter amends by re-running /setup.

## Red flags (setup-specific, additional to checkin's)

- Asking more than ~2 related questions in one message
- Writing standing items for a domain before the couple has agreed the
  domain exists
- Treating your proposed defaults as decisions
- Finishing without the charter written to ritual.md
