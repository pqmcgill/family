# Family Life Management Skill - Requirements

## Vision

A Claude skill that helps families manage the cognitive load of a busy, variable lifestyle - not by imposing rigid structure, but by surfacing what needs attention, tracking what's being neglected, and helping balance focus areas over time.

## Problem Statement

The core pain point is **cognitive load** - keeping track of everything that needs doing across multiple life domains, noticing when areas are being neglected, and balancing attention between focus areas and maintenance tasks. A rigid calendar doesn't work because family life is variable.

This system is designed for households where one partner carries the heaviest cognitive load (the **primary caregiver**) and the other serves as the **tech interface** who runs the system. The primary caregiver gets organized, paper-friendly output. The tech partner gets insights and talking points.

## Interaction Model

### Weekly Cycle

```
Sunday/Monday morning: Tech partner generates the week's plan via /family-plan
    ↓
Partners review/discuss together
    ↓
Primary caregiver takes the plan (paper checklist) and runs days autonomously
    ↓
Evening check-ins: Partners review the day together
    ↓
Tech partner logs what happened via /family-checkin
    ↓
System revises remaining week, surfaces insights:
  - What got done vs. what didn't
  - Areas being neglected (this week and over time)
  - Talking points (things to take on, rebalancing suggestions)
  - Opportunities to lighten the primary caregiver's load
    ↓
Repeat daily through the week
    ↓
End of week: System provides a retrospective view for next week's planning
```

### Key Interaction Characteristics

- **Primary caregiver never touches the tech.** Their interface is paper. Tech partner is the bridge.
- **The plan is a checklist, not a schedule.** Organized by domain/category, not by time slot. Fixed-time commitments are noted but the rest is flexible.
- **Evening check-in is the primary feedback loop.** Quick conversation → tech partner updates system → system recalculates.
- **The system generates talking points**, not just data. "You haven't done science in 2 weeks" is more useful than a raw log. "Personal time hasn't happened since last Tuesday" is actionable.
- **Tech partner can use the system to volunteer.** "What can I take on this week to help?" should have a good answer.

## Key Principles

1. **Reduce cognitive load, don't add to it** - The system should take things OFF the mental plate, not create new obligations
2. **Flexible, not rigid** - Accommodate variable days, not enforce a fixed schedule
3. **Surface neglect** - Proactively identify areas that haven't received attention
4. **Balance focus and maintenance** - Some areas need deep focus, others just need regular upkeep
5. **Whole-family view** - Coordinates across all family members, not just one person's task list
6. **Checklist, not calendar** - Organized by what needs doing, not when. Time-bound items are exceptions, not the rule.
7. **Caregiver autonomy** - They decide how to spend their day. The system suggests, they choose.
8. **Tech partner as operator** - They run the system, caregiver benefits from it. Low friction for both.
9. **Talking points, not prescriptions** - The system surfaces observations and suggestions. It does not dictate what to do or when. Exceptions: concrete breakdowns (laundry pipeline steps, hard schedule constraints) where specificity is the value.
10. **Iterative refinement** - All cadences, thresholds, and domains are starting points. The system must allow easy adjustment as the family learns what actually works.
11. **Pattern observation** - The system should notice behavioral patterns and surface them as insights, not just track against targets.
12. **Self-reflective** - The system should evolve its own behavior based on what's working and what isn't. When patterns emerge from usage — questions that are always noise, cadences that are wrong, domains that need restructuring — the system should propose and make changes to its own commands, requirements, and configuration. This is a living system, not a static one.
13. **Privacy boundary** - All personal information (names, ages, schedules, routines, family details) lives exclusively in `data/` (gitignored). The checked-in files (CLAUDE.md, REQUIREMENTS.md, commands) must remain generic and reusable. Any time the system modifies a checked-in file, it must validate that no personal information is being written and flag the user if it detects a leak.

## Life Domains

### MVP (Core Day-to-Day)

These are configured per-household via `/family-init`. Common domains include:

1. **Homeschool** - Subject tracking with configurable cadences. Some subjects are high-priority (daily/3x week), others are maintenance (weekly). Only tracked on designated school days.
2. **Household chores** - Two main components:
   - **Decluttering/cleaning** - habitual routine tracking
   - **Laundry** - pipeline-based tracking. Each load moves through stages (wash → dry → fold → put away). The system suggests which loads on which days and tracks pipeline state.
3. **Meals** - Not a meal planning system. Context-aware reminders (e.g., "prep dinner early on busy evenings"). Grocery trip tracking with pattern insights.
4. **Personal time** - Tracked per person. Caregiver's alone time is often critically neglected and should be treated as non-negotiable. Both partners track to prevent burnout.
5. **Admin/errands** - Bills/spending review (habitual) + one-off tasks (weekly catch-all bucket).
6. **Date night** - Quality time for partners. Requires coordination with childcare. Part of the anti-burnout strategy.

### Future / Aspirational (Not MVP)

- Health/wellness (exercise, appointments)
- Social/community (playdates, family events)
- Personal development (hobbies, reading)
- Home maintenance (repairs, seasonal, yard)

## Neglect Tracking

The system tracks how long each domain/item has gone without attention and surfaces it as talking points. This is observational ("it's been X days since Y") not prescriptive ("you must do Y today").

### How Neglect Gets Surfaced

The tone is collaborative and forward-looking, not accusatory:

- **During evening check-in**: Flags items crossing their configured thresholds
- **During weekly planning**: Highlights patterns from prior weeks
- **As conversation starters**: Arms the tech partner with observations; caregiver has agency in the response
- **Pattern insights**: Not just "did X happen" but "what patterns are emerging"
- **Over-time trends**: Longer horizon observations surfaced during weekly planning

### Time Horizons

- **Daily**: Laundry pipeline, dinner prep, decluttering, bills review
- **Weekly**: Homeschool subjects, groceries, personal time
- **Biweekly**: Date night
- **Monthly+**: Trend analysis across all domains

## Evening Check-in Format

### Design Principles
- **Fast enough to do tired at 9pm.** Should take 5 minutes or less on a typical night.
- **Q&A as the backbone, conversation as the escape hatch.** System asks consistent questions each night, but the tech partner can go off-script and elaborate when needed.
- **Consistent question format.** Same core questions each night so feedback on what's working vs. noise can accumulate.

### Core Questions (Nightly)

The system walks through each active domain, asking about:
1. **Homeschool**: Did homeschool happen today? _(Only on school days)_
2. **Laundry**: Pipeline-specific questions based on current state
3. **Meals**: Grocery trips, dinner prep notes (context-aware for busy evenings)
4. **Decluttering**: Did it happen tonight?
5. **Personal time**: Per person - did it happen? Brief note if yes.
6. **Bills/spending**: Did the nightly review happen?
7. **Variable/one-offs**: Anything come up or change about the rest of the week?

### System Response After Check-in

- Updated domain status
- Neglect flags that crossed thresholds
- Talking points (collaborative tone, forward-looking)
- Revised remaining-week checklist if assumptions changed
- Pattern observations when relevant (not every night)

## Weekly Plan Output

The system generates two views at the start of each week.

### View 1: By Domain (The Checklist)

Organized by life domain. Bullet points with checkboxes. No prose, no insights. Just what needs doing this week. Designed to be copied to paper.

Example:
```
HOMESCHOOL
[ ] Math (x3)
[ ] Reading (x3)
[ ] Science
[ ] Art
[ ] Music

LAUNDRY
[ ] Load 1
[ ] Load 2
[ ] Load 3
...

MEALS
[ ] Grocery run
[ ] (context-aware dinner notes)

PERSONAL TIME
[ ] Caregiver - at least once this week
[ ] Partner - at least once this week

ADMIN
[ ] Nightly bills/spending review
[ ] (one-off items)

DATE NIGHT
[ ] (if scheduled)

REMINDERS
- (items captured via /family-log)
```

### View 2: By Day (The Calendar View)

Next 7 days with hard schedule constraints shown. Not a prescribed plan - just the fixed scaffolding so the caregiver can see open windows.

### View Design Principles
- **Caregiver's view is bullet points and checkboxes.** No prose, no insights. Just the list.
- **Tech partner's view is conversational.** Insights, talking points, pattern observations.
- **Both views are starting points**, not mandates.
- **Granularity is high-level.** "Do math" not "Do math workbook pages 12-14."
- **Hard constraints are shown for planning context**, not because they aren't known.

## Weekly Planning Session

### Format
Conversational Q&A. The system walks the tech partner through a structured set of topics but allows rabbit holes. When a tangent has been explored, the system gently steers back.

### Flow

1. **Review last week** - Summary of what got done, what didn't, patterns. Discussion.
2. **Variable events this week** - Unusual calendar items, schedule changes.
3. **Domain walk-through** - System goes through each domain with context-aware suggestions.
4. **Generate outputs** - Both views for caregiver, insights summary for tech partner.
5. **Confirm and close** - Final adjustments before locking in.

### Design Principles
- **Cover all the bases** - No domain gets skipped in planning, even if the answer is "nothing this week."
- **Rabbit holes welcome, but managed** - Deep dives are fine; system brings it back.
- **Last week informs this week** - Neglect data and patterns feed into suggestions.
- **Caregiver can participate or not** - Sometimes present, sometimes relayed.

## Data Model

### Approach
Simple local files. Prototype - keep it minimal and migrate later if needed.

### Storage Location
`data/` (gitignored - contains personal information)

### Structure
```
data/
├── config/
│   ├── domains.yaml          # Domain definitions, cadences, thresholds
│   ├── schedule.yaml         # Fixed weekly commitments
│   └── laundry-loads.yaml    # Load types and pipeline stages
├── weeks/
│   └── YYYY-WXX/
│       ├── plan.md           # Generated weekly plan (both views)
│       ├── checkins/
│       │   ├── mon.md        # Evening check-in log
│       │   └── ...
│       └── insights.md       # System-generated insights for the week
├── state/
│   └── current.yaml          # Running state (laundry pipeline, last-done dates)
└── history/
    └── trends.md             # Longer-term pattern observations (updated weekly)
```

### Generated by /family-init

All files under `data/config/` and `data/state/` are generated by the `/family-init` command, which walks the user through a household discovery conversation covering:
- Family members and roles
- Weekly schedule and fixed commitments
- Life domains and priorities
- Cadences and thresholds
- Specific routines and context

### Principles
- **Text-first.** Markdown and YAML. Human-readable, easy to inspect.
- **Week is the primary unit.** Each week gets its own folder.
- **State is minimal.** Just enough to track "last done" dates and in-progress items.
- **All personal data is local.** Nothing personal is checked into version control.
- **Migrate later, not now.** If this outgrows flat files, move to SQLite or similar.

## Design Constraints

- Must work as a Claude Code skill (file-based, conversational)
- Should be low-friction to use daily
- Data should live locally
- All data is plain text (markdown/yaml) - human-readable
- No external dependencies or services for MVP
- Personal data must never be checked into version control
