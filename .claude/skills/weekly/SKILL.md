---
name: weekly
description: Use when the user starts a weekly review or planning session, says "weekly", "plan the week", or wants the full sweep — every open item, neglect, fairness, trends — before building next week's plan.
---

# Weekly Review & Planning

Same hard rules as the nightly check-in skill: read the "Hard rules"
and "Red flags" sections of `.claude/skills/checkin/SKILL.md` FIRST and
apply all of them identically (CLI only; read before you think; full
batch then confirm then write; never guess facts; aliases only; facts
vs. inference; every write carries `--source weekly` or
`--source transcript`). Differences are in scope and flow.

## Flow

1. Run, before interpreting any user input:
   - `./bin/fam backup`
   - `./bin/fam check` (event-log integrity — investigate any drift
     before writing anything new)
   - `./bin/fam --source weekly horizon` (EVERY open item, however far out)
   - `./bin/fam --source weekly chore list`
   - `./bin/fam --source weekly fair --weeks 4`
   - read `ritual.md`
2. **Review phase** — walk through, conversationally:
   - Last week's pending entries: `fam week new` REFUSES to draft while
     any earlier week has pending entries, so disposition each now —
     `fam week done <id>` (it happened) or `fam week skip <id>` (let it
     go, on the record). Items to carry forward: skip now, re-add to the
     new week in the planning phase (with `--day`, and `--todo` if it
     mirrors a todo).
   - Far-out dated items: anything that needs action to start now?
   - Parked todos: still parked, or revive (`fam todo defer <id> --to <date>`)
     or drop?
   - Unresolved calendar (date passed): done, or cancelled?
   - Neglect flags: name them plainly ("bedding is at 24 days, usually ~14").
   - Fairness: present the numbers; if lopsided, ask — never accuse.
   - Pulse trends: facts first, then any "I notice ..." inference
     (not saved unless asked).
   - Observations: do NOT revalidate the list — that's homework, not
     review. Raise one only if (a) this session's facts contradict it,
     or (b) it's the oldest and unconfirmed for 30+ days — at most 2
     per session. Archive (`fam obs archive <id>`) only on agreement.
3. **Planning phase** — only after review:
   - `./bin/fam --source weekly week new` drafts the week from standing
     chores. Run it AFTER the user agrees planning is starting (it writes).
     CAUTION: `week new` defaults to the week CONTAINING today. On the
     Sunday planning day that's the week that's *ending* — pass
     `--start <upcoming Monday>` to draft the week ahead. Verify the
     "week of <date>" echo before continuing; undo + redo if wrong.
   - Adjust the draft through conversation: skip entries
     (`fam week skip <id>`), add one-offs (`fam week add ... --kind oneoff`).
     A one-off that mirrors an open todo gets `--todo <id>` (or
     `fam week link <eid> <tid>` after the fact) so marking the entry
     done resolves the todo too — never track the same work twice
     unlinked.
   - Plan personal time blocks for BOTH adults — ask each
     (`fam week add "<block>" --kind personal --who <alias>`).
   - **Assign days**: once the family agrees which day each entry lands
     on, set it — `fam week day <id> <mon..sun>` (validated; works on
     standing-drafted entries too). `fam today` and the checkin report
     compute TODAY'S TARGETS and BEHIND PLAN from this field; an entry
     left unassigned shows under NO DAY ASSIGNED so it can't hide.
     `fam week note` remains for free-text context ("before the trip").
   - **Assign owners** where the family knows who's doing what
     (`--who` on add) — the fairness report can only measure owned work.
   - Standing items themselves: add, pause, resume, or retire?
4. Save the session journal (`--session weekly --kind summary`, plus any
   pasted transcript as `--kind transcript`). Also write a terse one-line
   day-plan (`--session weekly --kind summary`, prefix `WEEKPLAN`, kept
   under 200 chars) capturing each day's targets — laundry loads, room
   resets, key events. This is a human-readable summary; the entry
   notes set in step 3 are the structured copy. If the two would ever
   disagree, fix the notes — they win.
5. **Verification replay** — same as nightly: list all WROTE echoes
   against what was agreed, confirm, fix with `fam undo` if wrong.

## Order matters

Review BEFORE planning. The whole point of the weekly is that next
week's plan is informed by the full horizon, neglect, and fairness
facts — a plan made before the review silently repeats last week's
blind spots.

## Self-adjustment

Same mechanism as the checkin skill: ritual.md for preferences (no
commit), this SKILL.md for behavior (commit after confirming diff).
