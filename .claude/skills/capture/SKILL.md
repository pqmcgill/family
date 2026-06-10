---
name: capture
description: Use when the user drops a quick note, voice transcript, or mid-day update outside a check-in — "capture this", "add this", "quick note", "grabbed groceries" — anything that should be recorded now without running the full nightly or weekly session.
---

# Quick Capture

Minimal flow — no ritual, no review, no pulse. Same hard rules as the
nightly check-in skill: read the "Hard rules" and "Red flags" sections
of `.claude/skills/checkin/SKILL.md` FIRST and apply all of them
identically (CLI only; full batch then confirm then write; never guess
facts; aliases only; every write carries `--source capture` or
`--source transcript`).

## Flow

1. Take the user's note or transcript.
2. If interpreting it needs current state (e.g. "mark the towels done"
   needs the week-entry id), run `./bin/fam --source capture checkin`
   — never guess ids, never assume an item is new when it might map to
   existing state.
3. Propose the extracted changes as one batch, with exact commands.
   Unknown people → propose `fam person add`. Ambiguity → ask.
4. On confirmation: execute the writes; store the raw input:
   `./bin/fam --source capture journal add --session capture --kind
   transcript --text "..."` (verbatim input) or `--kind summary` (short
   notes you've restated).
5. Echo the WROTE lines back as confirmation. Done — exit. No pulse,
   no review, no "while we're at it."

## What capture is NOT

- Not a mini check-in: don't review neglect flags, don't ask about the
  day, don't prompt for pulses.
- Not a place to skip confirmation because the note "is obvious."
