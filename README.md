# Family Life Management System (My Family. YMMV)

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill-based system for managing the cognitive load of a busy family — not by imposing rigid structure, but by surfacing what needs attention, tracking what's being neglected, and helping balance focus areas over time.

This was built for one specific household — a homeschooling family where one partner is analog-first (paper checklists, handwritten notes) and the other runs things through a CLI. The domains, roles, and workflows reflect what works for us. Your family probably looks different, and that's the point: clone it, run `/family-init`, and reshape it to fit your life. Everything here is a starting point, not a prescription.

## The Problem

Family life generates an enormous amount of cognitive load: tracking homeschool subjects, laundry pipelines, grocery runs, personal time, household chores, date nights, appointments, and all the one-off tasks that accumulate throughout the week. Often this load falls unevenly on one person.

Calendars and rigid scheduling don't work for variable family lifestyles. What helps is a system that **observes, tracks, and surfaces** — so the humans can make good decisions with less mental overhead.

## How It Works

This system runs as a set of Claude Code slash commands. In our household, one partner operates the system and the other gets paper-friendly output — but `/family-init` lets you define whatever roles and workflows make sense for yours.

```
Sunday/Monday:  /family-plan    → Weekly planning session, generates checklist + insights
Every evening:  /family-checkin → 5-minute structured Q&A, logs what happened
Any time:       /family-edu     → Track education activities against state standards
Any time:       /family-log     → Quick capture ("we need new shoes, return library books")
Any time:       /family-status  → Glance at current state across all domains
```

### Weekly Cycle

```
Plan the week (conversational Q&A)
    ↓
Work through the week with a checklist
    ↓
Evening check-ins capture what happened
    ↓
System tracks neglect, surfaces patterns, generates talking points
    ↓
Repeat → feed insights into next week's plan
```

## Key Design Principles

- **Checklist, not calendar.** Organized by what needs doing, not when.
- **Talking points, not prescriptions.** The system surfaces observations ("it's been 5 days since math"); the humans decide what to do.
- **Configurable audiences.** Different people can get different output styles — bullet-point checklists, conversational insights, or both.
- **Self-reflective.** The system evolves its own commands and configuration as patterns emerge from usage.
- **Privacy-first.** All personal data stays local and gitignored. Checked-in files contain zero personal information.

## Getting Started

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and configured
- [uv](https://docs.astral.sh/uv/) (for the vector store and standards ingestion scripts)

### Setup

1. Clone this repo:
   ```bash
   git clone https://github.com/pqmcgill/family.git
   cd family
   ```

2. Configure the git hooks:
   ```bash
   git config core.hooksPath .githooks
   ```

3. Run the setup command in Claude Code:
   ```
   /family-init
   ```

   This walks you through a discovery conversation about your household — family members, weekly schedule, life domains, priorities — and generates all the config files the system needs.

4. Start your first week:
   ```
   /family-plan
   ```

## What Gets Tracked

The system is organized around **life domains**, each with configurable cadences and neglect thresholds. These are examples from our setup — yours will be different after running `/family-init`:

| Domain | What it tracks | Example cadence |
|--------|---------------|-----------------|
| **Homeschool** | Subjects completed per week | Math 3x/week, Art 1x/week |
| **Laundry** | Multi-stage pipeline (wash → dry → fold) per load type | ~1 load/day |
| **Meals** | Grocery trips, dinner prep context | Weekly + daily |
| **Personal time** | Per-person alone time | 1x/week minimum |
| **Chores** | Decluttering, cleaning routines | Nightly |
| **Admin** | Bills review, one-off tasks | Nightly + as needed |
| **Date night** | Partner quality time | Biweekly |

Domains, cadences, and thresholds are all configurable. Add what matters to your family, remove what doesn't.

## Semantic Search

The system maintains a local vector store (LanceDB + sentence-transformers) that indexes all historical data — check-ins, weekly plans, education logs, and current state. Skills query it automatically to surface relevant context without reading every file.

Each evening check-in captures three layers of data:

1. **Structured fields** — domain-by-domain data points (dates, pipeline stages, yes/no)
2. **Journal** — a short narrative paragraph capturing what the day *felt like*, confirmed by the user
3. **Vibe** — a one-line energy/mood summary

The structured data supports direct queries ("when did groceries last happen"). The journal and vibe entries give the vector store rich text for fuzzier pattern matching across weeks — things like energy trends, recurring stressors, or what conditions lead to good days vs. rough ones.

```bash
# Rebuild the full index from flat files
uv run --project scripts/vector-store vector-store rebuild

# Search across all historical data
uv run --project scripts/vector-store vector-store search "wife personal time patterns"

# Check index status
uv run --project scripts/vector-store vector-store status
```

The flat files remain the source of truth. The vector store is a derived index, rebuildable at any time.

## Education Tracking

`/family-edu` maps real-world learning activities to state academic standards (Indiana K-5). It supports four modes:

- **Log activities** — describe what happened, the system maps to standards
- **Review coverage** — see which standards have been touched and where gaps exist
- **Build baseline** — capture what's already mastered without activity-by-activity history
- **Explore standards** — browse what a subject or grade level covers in plain language

Standards are tracked independently — advanced work is celebrated but never used to assume lower-level mastery. The caregiver is the subject-matter expert; the system captures and organizes their knowledge.

## Data Layout

```
data/                        # gitignored — all personal data stays local
├── config/
│   ├── domains.yaml         # Domain definitions, cadences, thresholds
│   ├── schedule.yaml        # Fixed weekly commitments
│   ├── laundry-loads.yaml   # Load types and pipeline stages
│   └── .sensitive-terms     # Terms blocked from checked-in files
├── state/
│   └── current.yaml         # Running state (updated by check-ins)
├── edu/                     # Education tracking
│   ├── coverage.yaml        # Standards coverage state
│   └── activity-log/        # Logged activities mapped to standards
├── vector_store/            # LanceDB index (auto-generated, rebuildable)
└── weeks/
    └── YYYY-WXX/
        ├── plan.md           # Weekly plan (checklist + insights)
        ├── insights.md       # Pattern observations
        └── checkins/         # Daily check-in logs
```

Everything under `data/` is generated by `/family-init` and updated by the other commands. Personal data is sent to your LLM provider during conversations but is never checked into version control.

## Privacy

This system is designed to be shared publicly while keeping personal data out of version control. It is **not** a fully local system — personal data is sent to Anthropic's API (or whichever LLM provider you use) during every conversation. The privacy boundary here is about public exposure, not third-party access.

- **`data/`** is gitignored — config, state, and weekly logs are not checked into the repo
- **Checked-in files** contain only generic design docs and command templates
- **A pre-commit hook** scans staged changes against your `data/config/.sensitive-terms` file and blocks commits that would leak personal information into the public repo
- **CLAUDE.md** instructs the system to validate content before writing any tracked file

**Know your comfort level.** Only track data you're comfortable sending to a third-party API. For example, we use role labels ("Wife", "Kid 1") instead of real names — that's a boundary that feels right for our family. Yours may be different. If you want true privacy, you could run this with a local model instead of a cloud provider. The system doesn't depend on any specific LLM — it's just files and prompts.

## Philosophy

This system is built around a few observations:

1. **One person usually carries most of the cognitive load.** The system makes that visible and helps rebalance it.
2. **Families don't run on schedules.** They run on "what needs doing" with some fixed commitments layered on top.
3. **Noticing neglect is more valuable than planning perfection.** "Science hasn't happened in 3 weeks" is more useful than a color-coded daily schedule.
4. **The system should get better over time.** It's self-reflective — when something isn't working, it proposes changes to its own behavior.

## License

MIT
