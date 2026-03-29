# Roadmap

## In Progress

### UX Research Through Real-World Usage

This system is in active daily use. The current priority is sustained real-world testing to understand what actually works — which questions are noise, which cadences are wrong, which domains need restructuring, and where the interaction model breaks down. Design changes are driven by lived experience, not speculation.

### Data Architecture Evaluation

The current flat-file approach (YAML + Markdown) optimizes for human readability and simplicity. As historical data accumulates, this may not scale well for the kind of pattern analysis and trend surfacing the system aspires to. A local indexed database (e.g., SQLite) could enable richer agent-driven insights across weeks and months of data. The plan is to let real usage reveal the pain points before committing to a migration.

## Future Considerations

### Onboarding Improvements

The `/family-init` flow currently requires a fairly long discovery conversation. Streamlining this — perhaps with sensible defaults, progressive disclosure, or the ability to import from existing tools — would lower the barrier to adoption.

### Multi-Week Trend Analysis

The system currently operates on a weekly cycle with some cross-week awareness. Deeper longitudinal analysis (monthly patterns, seasonal shifts, long-term neglect trends) would make the weekly planning sessions significantly more insightful.

### Voice / Natural Language Input

The evening check-in is designed to be fast, but typing answers into a CLI at 9pm is still friction. Voice transcription or more conversational free-form input could make the daily loop feel lighter.

### Shareable Output Formats

The caregiver's checklist is designed for paper, but getting it there requires manual copy/paste. Direct export to printable formats, shared notes apps, or even a simple web view could reduce the bridge between system output and daily use. Google Docs integration via MCP is a natural fit — generating a shared, auto-updating weekly doc that the caregiver can pull up on any device.

### Configurable Reminder Cadences

Currently the system only surfaces information when you ask for it. Proactive nudges — via notifications, scheduled agents, or integrations with existing tools — could catch things that slip between check-ins.

