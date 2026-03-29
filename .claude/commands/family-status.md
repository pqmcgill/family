You are providing a quick status view of the family management system.

## Setup
1. Read `data/config/domains.yaml` for domain definitions and thresholds.
2. Read `data/state/current.yaml` for current tracking state.
3. Read this week's plan and any check-ins from `data/weeks/YYYY-WXX/`.

If `data/config/domains.yaml` doesn't exist, tell the user to run `/family-init` first.

## Output

Provide a concise status report. Natural language, conversational tone. Use names from the config files.

### Structure

1. **Today is [day].** Note any fixed commitments from the schedule.

2. **Domain status**: For each MVP domain, one line:
   - Last done date (or "never tracked")
   - Whether it's approaching or past its neglect threshold
   - Any in-progress items (laundry pipeline)

3. **Neglect alerts**: Call out anything past threshold. Prioritize by severity.

4. **This week so far**: Quick summary of what's been checked off vs. what's still open from the weekly plan.

5. **Laundry pipeline**: Current state of each load type.

Keep it brief. This is a glance, not a planning session.
