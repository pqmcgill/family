# Family Education Tracking — Requirements

## Vision

A Claude skill (`/family-edu`) that helps a homeschooling family track their child's learning against Indiana Academic Standards. Not a curriculum planner or daily tracker — a conversational tool that maps real-world activities to standards, tracks coverage over time, and surfaces gaps and insights on demand.

## Problem Statement

Homeschool families do rich, varied learning every day — building, playing, exploring, reading, gaming — but mapping that activity back to state standards is tedious. Existing tools use Common Core, which doesn't align with Indiana's standards. The family needs a system that:

1. Takes natural-language descriptions of what happened and maps them to Indiana standards
2. Tracks which standards have been covered, how recently, and how thoroughly
3. Surfaces gaps — what hasn't been touched, what was covered long ago and may need revisiting
4. Recognizes when activities hit above grade level without assuming mastery of everything below
5. Builds its baseline from the caregiver's existing knowledge, not from scratch

## Interaction Model

### Who Uses It

- **Patrick** types. **Wife** is the subject-matter expert on what Kid 1 has learned and is learning.
- Sessions are conversational between both partners, with Patrick entering data.
- Same pattern as other family skills — warm, efficient, no jargon.

### Cadence

- **Ad-hoc.** Not tied to daily check-ins or weekly planning.
- Used when the family wants to:
  - Log a batch of recent activities and see what standards they hit
  - Review coverage and find gaps
  - Build or update the baseline of what's already been mastered
  - Check whether a specific area needs attention

### Session Types

The skill should support several modes, selectable at the start or inferred from context:

1. **Log activities** — "Here's what we did recently." System maps to standards, confirms, records.
2. **Review coverage** — "Where are we?" System shows standards coverage by subject/domain, highlights gaps, flags things that haven't been touched in a while.
3. **Build baseline** — "She already knows X." Conversational walkthrough to establish existing mastery without requiring activity-by-activity history.
4. **Explore a standard** — "What does 2nd grade geometry look like?" System shows the standards in plain language with examples of activities that could meet them.

## Standards Framework

### Source

Indiana Academic Standards (IAS). These are publicly available and organized by:
- **Subject** (Math, ELA, Science, Social Studies, etc.)
- **Grade level** (K, 1, 2 — with awareness of 3-5 for above-level work)
- **Domain/strand** within each subject
- **Individual standards** within each domain

### Grade Range

- **Primary focus: K-2.** This is where tracking matters most right now.
- **Awareness of 3-5.** When an activity clearly maps to a higher standard, note it — but don't add it to the coverage tracking unless explicitly asked. The point is to celebrate ("that was 4th grade level!") not to create tracking obligations.

### Critical Rule: No Implied Mastery

If Kid 1 completes an activity that maps to a 5th-grade geometry standard, the system must NOT assume mastery of K-4 geometry standards. Each standard is tracked independently. The system should:
- Note the advanced work
- Ask whether related lower-level standards have been covered
- Surface the gap explicitly: "This hit 5th-grade geometry. You haven't logged anything for 2nd-grade geometry yet — is that covered, or something to revisit?"

## Data Model

### Storage

```
data/
├── edu/
│   ├── standards/           # Indiana standards reference data
│   │   ├── math-k.yaml
│   │   ├── math-1.yaml
│   │   ├── math-2.yaml
│   │   ├── ela-k.yaml
│   │   └── ...
│   ├── coverage.yaml        # Standards coverage state
│   └── activity-log/        # Logged activities mapped to standards
│       └── YYYY-MM-DD.md    # (or batched by session)
```

### Standards Reference

Each standard should be stored with:
- **ID** (e.g., `IN.Math.2.G.1`)
- **Grade level**
- **Subject and domain**
- **Description** (official language)
- **Plain-language summary** (what it means in practice)
- **Example activities** (things a homeschool family might do that would meet this)

### Coverage Tracking

For each standard:
- **Status**: `not_started`, `introduced`, `practiced`, `mastered`, `revisit_needed`
- **Last touched**: date
- **Activity references**: which logged activities mapped here
- **Notes**: any context from Wife about mastery level
- **Source**: `baseline` (from initial setup) or `activity` (from logged activities)

### Activity Log

Each logged session records:
- Date
- Natural-language description of activities
- Mapped standards (with confidence: `clear_match`, `partial`, `tangential`)
- Any notes or context

## Skill Behavior

### `/family-edu`

On launch, the skill should:
1. Check if `data/edu/coverage.yaml` exists. If not, offer to start with baseline setup.
2. If state exists, ask what the family wants to do: log activities, review coverage, build more baseline, or explore standards.

### Activity Logging Flow

1. User describes activities in natural language (as casually as they want)
2. System maps each activity to relevant Indiana standards
3. System presents the mapping for confirmation: "Here's what I see that covering..."
4. User confirms, adjusts, or adds context
5. System records and updates coverage

### Coverage Review Flow

1. System presents a summary by subject and domain
2. Highlights:
   - Standards not yet touched
   - Standards last covered 6+ months ago (configurable threshold)
   - Areas where coverage is thin vs. deep
   - Above-grade-level work noted
3. For each gap or flag, ask: "Is this covered and we just haven't logged it, or is this a real gap?"

### Baseline Building Flow

1. Walk through subjects one at a time
2. For each domain, describe what the standards cover in plain language
3. Ask Wife where Kid 1 stands: mastered? familiar? not yet?
4. Record her assessment as baseline data
5. Don't rush — this can happen across multiple sessions

### Insights (Surfaced During Any Session)

- "You haven't logged any science in 3 months — is that intentional?"
- "Kid 1's math is tracking at 2nd-3rd grade across the board, except measurement, which hasn't come up since September."
- "Today's block building covers 1st-grade geometry (shapes and attributes). You logged 3rd-grade geometry last month with the architecture project — want to confirm 2nd-grade geometry is solid?"
- "ELA standards are well-covered through daily reading. The gap is in writing/composition."

## Key Principles

1. **Wife is the expert.** The system captures and organizes her knowledge. It does not second-guess her assessments.
2. **Activities first, standards second.** The family describes what they did. The system does the mapping work. Never the reverse — this isn't a curriculum that tells them what to do.
3. **No implied mastery.** Every standard is tracked independently. Advanced work is celebrated, not used to skip fundamentals.
4. **Conversational, not clinical.** Same tone as other family skills. This is two tired parents talking about their kid's learning, not a compliance exercise.
5. **Incremental.** Baseline doesn't need to be complete on day one. Coverage builds over time. Gaps are observations, not failures.
6. **Ad-hoc, not obligatory.** This tool is here when they want it, not another thing on the checklist.
7. **Privacy boundary.** All data in `data/edu/` (gitignored). No child names, specific details, or assessment data in checked-in files.

## Open Questions

- **Standards data ingestion**: How to get Indiana Academic Standards into a structured format the system can reference? Options: manual entry for K-2, web fetch of published standards, or pre-built reference files. Needs research.
- **Granularity**: Indiana standards vary in specificity. Some are broad ("demonstrate understanding of..."), some are narrow ("count to 120 starting at any number"). How granular should tracking be?
- **Cross-subject mapping**: Some activities hit multiple subjects (e.g., a cooking project covers math, reading, science). The system should handle multi-mapping naturally.
- **Reporting**: Will the family ever need a formal-ish report (e.g., for annual assessment requirements in Indiana)? If so, that shapes output format.

## Not In Scope (For Now)

- Curriculum planning or activity suggestions ("you should do X to cover Y")
- Multiple children (Kid 2 will eventually need this, but one child for now)
- Integration with external tools or platforms
- Formal lesson plan generation
