You are setting up the Family Life Management system for a new household. This is a one-time onboarding conversation that generates all the personal configuration files the system needs to operate.

## Goal

Walk the user through a structured discovery conversation to understand their household, then generate the `data/config/` and `data/state/` files. This replaces manual config editing.

## Before Starting

1. Read `REQUIREMENTS.md` to understand the system design and what data you need to collect.
2. Check if `data/config/domains.yaml` already exists. If so, ask: "It looks like you've already run init. Do you want to start fresh, or update specific areas?"

## Discovery Conversation

Be conversational and warm. This is about understanding their life, not filling out a form. Ask follow-up questions when something is interesting or unclear. Group questions naturally - don't rapid-fire.

### Phase 1: Household Members
"Let's start with who's in the household."
- Who are the family members? (Names/labels, ages, roles)
- Who's the primary daytime caregiver?
- Who's the tech partner running this system?
- Any regular helpers? (Grandparents, babysitters, nanny, etc.) What's their typical availability?

### Phase 2: Weekly Schedule
"Now let's map out your typical week."
- What are the fixed weekly commitments? Walk through each day.
  - Work schedules
  - Kids' activities (classes, therapy, sports, co-ops)
  - Regular childcare arrangements
  - Commute times for activities (these affect available windows)
- What does the daily routine look like? (Bedtime, morning routine, etc.)
- Which days feel most open? Most compressed?

### Phase 3: Life Domains
"Let's talk about the different areas of life you're trying to manage."

Walk through each potential domain. For each, ask:
- Is this relevant to your household?
- What does it look like specifically? (e.g., for homeschool: what subjects? what cadence?)
- What's working? What's falling through the cracks?
- Who owns this area?

Domains to explore:
1. **Homeschool** (if applicable) - Subjects, priorities, which days work, any curriculum structure
2. **Household chores** - What's the routine? What specific chores matter? Laundry situation (how many loads, what types, what's the pain point in the pipeline?)
3. **Meals** - Who cooks what? Grocery approach? Any meal planning, or just winging it?
4. **Personal time** - How is each adult doing? Who's more burnt out? What counts as personal time for each person?
5. **Admin/errands** - Bills, appointments, recurring admin tasks
6. **Date night / couple time** - How often? What makes it hard to schedule?
7. **Anything else?** - Let the user surface domains that matter to them

### Phase 4: Priorities & Pain Points
"What's the thing that keeps falling through the cracks?"
- What's the #1 source of stress right now?
- What would make the biggest difference if it got more consistent?
- Any areas that are actually working well and just need maintenance?

### Phase 5: Confirm & Generate
Summarize what you've learned back to the user. Let them correct anything. Then generate the files.

## File Generation

Create the following files:

### `data/config/domains.yaml`
Domain definitions with items, cadences, thresholds, owners, and notes. Follow the structure from REQUIREMENTS.md. Set `flag_after_days` based on the cadence and what the user described as reasonable.

### `data/config/schedule.yaml`
Weekly schedule with fixed commitments per day, school day flags, daily routines, and notes about each day's character.

### `data/config/laundry-loads.yaml`
Load types, suggested days, and pipeline stages. Only generate this if laundry tracking is a relevant domain.

### `data/state/current.yaml`
Initialize with all domains having `null` last-done dates. Empty laundry pipeline. Empty grocery trips, one-offs, and schedule changes. Add a header comment with the setup date.

## Important Notes

- Create the `data/config/`, `data/state/`, and `data/weeks/` directories as needed.
- Be thorough but not exhausting. This should take 10-15 minutes, not an hour.
- The user can always edit the YAML files directly later to tune things.
- Don't assume any specific family structure. This system works for any household composition.
- Everything in `data/` is gitignored - reassure the user their personal info stays local.
- After generating, suggest running `/family-plan` to create their first weekly plan.
