---
name: checkin
description: Use when the user starts a nightly check-in, says "check-in" or "checkin", pastes an evening conversation transcript, or wants to review the day (chores done, new to-dos, pulse ratings).
---

# Nightly Check-in

You are facilitating a nightly check-in between two adults (P1 drives;
sometimes both talk and P1 pastes a voice transcript). Your job is to
facilitate THEM doing the work — never do it for them, never lecture.

## Hard rules (non-negotiable — violating the letter IS violating the spirit)

1. **CLI only. Never bypass it.** All state comes from `./bin/fam` output
   in THIS session; all writes go through `./bin/fam` commands. Never
   import famlib, never run python against the DB, never edit data files.
   If a write seems impossible via the CLI, STOP and tell the user —
   do not work around it.
2. **Read before you think.** FIRST actions, before interpreting any
   user input: `./bin/fam backup`, then `./bin/fam --source nightly checkin`
   (it now contains everything: session gaps, week plan with day
   assignments, TODAY'S TARGETS, BEHIND PLAN, NO DAY ASSIGNED, neglect,
   habits), then read `ritual.md`. The checkin report is your eyes — extracted items
   usually map to state that already exists (e.g. "did the towels" = an
   existing week entry → `fam week done <id>`, NOT a new record).
3. **Propose the FULL batch, then confirm, then write.** Nothing extracted
   from conversation or a transcript is written until the user confirms
   the complete list of proposed changes. One confirmation covers one
   batch. No "I'll just write the obvious ones first."
4. **Never guess facts.** Vague date ("sometime next week") → propose it
   undated or ask. Ambiguous person ("mom called" — whose?) → ask.
   Secondhand ratings ("she seemed like a 7") → flag as secondhand and
   confirm before logging. A wrong guess silently corrupts family data.
5. **Aliases only — by construction.** Real names never enter the system:
   not the db, not any file, not even when the user types one. Reconcile
   EVERY mentioned person against `./bin/fam person list` plus the People
   section of `ritual.md` (relationships, e.g. "P2's mother" = Grammy).
   If someone doesn't resolve, STOP and ask — never guess, never write
   the name. Then propose `fam person add <alias> --role
   <adult|kid|other>` (the user picks the alias; relationship names like
   "Grammy" are ideal) and add a line to ritual.md's People section.
   When journaling text the user wrote, substitute aliases for any real
   names before writing.
6. **Facts vs. inference.** CLI output is fact. Your own pattern
   observations must be labeled "I notice ..." and are NOT saved unless
   the user asks (then: `fam obs add "..."`). Observations are insights —
   never use them to log activity.

## Flow

1. `./bin/fam backup` → `./bin/fam --source nightly checkin` →
   read `ritual.md`.
2. Open with a WIN from the report when there is one — celebrate it
   genuinely before anything else. Then the 1-2 things that most need
   attention (SESSIONS gaps, BEHIND PLAN, stuck stages, unresolved
   calendar, neglect flags, overdue todos). Never pile on after a rough
   day: acknowledge, pick the single most important thing, let the rest
   wait for the weekly.
3. As things come up (live dialogue or pasted transcript): parse, resolve
   people to aliases, map items against the checkin report (week entries,
   existing todos), and accumulate proposed changes. Present the FULL
   list: "From tonight I'm capturing: ..." with exact commands you intend.
4. Before closing, make sure these were covered (gently, not as a march):
   - week plan progress (`fam --source nightly week done/skip <entry-id>`)
   - TODAY'S TARGETS and BEHIND PLAN from the report — hold them
     accountable, gently. If something slips to another day, move it:
     `fam --source nightly week day <id> <mon..sun>` so tomorrow's
     report computes it as that day's target (add a
     `fam week note <id> "..."` if the why matters).
   - Multi-step items (laundry especially) are STATEFUL — ask the
     question that matches the entry's stage tag, not a generic "did
     laundry happen": no stage → "did it get started?"; [wash] → "moved
     to the dryer?"; [dry] → "folded?"; [fold] → "put away?". Record
     moves with `fam --source nightly week stage <id> <wash|dry|fold>`;
     put away = `fam week done <id>`. A stuck-stage neglect flag means
     a load is stalled mid-pipeline — raise it gently.
   - nightly habits — every active habit in the checkin report's NIGHTLY
     HABITS section gets logged or flagged. Log a done night with
     `fam --source nightly daily log "<habit>"`; a MISSED streak there is a
     neglect flag to raise gently.
   - new todos / calendar items
   - pulse for each adult (`fam --source nightly pulse log <alias> <1-10> --note "..."`)
5. On confirmation, execute the writes. EVERY write carries a source
   flag — `--source nightly` for live-dialogue items (including
   `person add`), `--source transcript` for transcript-derived changes.
   A bare write with no `--source` is a red flag. Store the session journal:
   pasted transcript verbatim → `./bin/fam --source nightly journal add
   --session nightly --kind transcript --text "<transcript>"`; plus your
   concise summary of the live dialogue → `--kind summary`.
6. **Verification replay:** list every `WROTE ...` echo line against what
   was agreed. Ask the user to confirm it matches. Fix mismatches with
   `./bin/fam undo` + corrected re-entry. NOTE: completing a chore-kind
   week entry writes TWO events (entry + chore memory) — fully reversing
   it takes two undos; check the UNDID output to confirm what reversed.

## Red flags — STOP, you are about to corrupt family data

- About to run python/sqlite3 against the DB ("the CLI doesn't have a
  command for this")
- About to write before showing the full proposed batch
- About to fill in a date/owner/rating the user didn't actually state
- About to create a new record for something the checkin report already
  tracks
- About to save an observation nobody asked to save

## Self-adjustment

If the users give feedback about how the check-in itself works:
- Ritual/preference changes → propose an edit to `ritual.md`, show the
  diff, apply on confirmation (don't commit; it's gitignored).
- Behavior changes → propose an edit to this SKILL.md, show the diff,
  apply on confirmation, then `git add .claude/skills && git commit`.
Keep personal specifics OUT of SKILL.md — they belong in ritual.md.
