# Roadmap

## In Progress

### Education Standards Tracking (`feature/family-edu`)

A `/family-edu` skill for tracking homeschool learning against Indiana Academic Standards (K-2 focus, 3-5 awareness). Currently in design phase — requirements and technical design are complete, implementation is next.

- **Requirements**: [REQUIREMENTS-EDU.md](REQUIREMENTS-EDU.md)
- **Technical design**: [DESIGN-EDU-STANDARDS.md](DESIGN-EDU-STANDARDS.md)
- **Branch**: `feature/family-edu`

The system ingests public Indiana Academic Standards from IDOE PDFs and the OpenSALT API, validates across sources, and produces structured YAML reference files. The parsed standards data and ingestion tooling are public (committed to git); family usage data (coverage tracking, activity logs) stays private. The skill lets the family log activities, map them to standards conversationally, track coverage, and surface gaps — all driven by the caregiver's expertise, not the system's.

**Repo scope**: Developing here while we iterate, but this may break out into its own project. The standards data, ingestion pipeline, and validation tooling are fully general — useful to any Indiana homeschool family, not tied to this family's workflow. The natural split: standards data + ingestion pipeline become a standalone repo; the family-specific coverage tracking and conversational interface stay here.

**Interface**: Starting with a `/family-edu` Claude Code skill as the conversational layer, but the design intentionally doesn't couple to it. The data schema (standards YAML + coverage YAML) is the contract. Any LLM chat, web UI, or future tool that can read the files can provide the same interaction. The skill is a thin prompt template over a well-structured data layer.

**Next steps**: Build ingestion pipeline and adapters, parse K-2 standards, implement the `/family-edu` skill.

### UX Research Through Real-World Usage

This system is in active daily use. The current priority is sustained real-world testing to understand what actually works — which questions are noise, which cadences are wrong, which domains need restructuring, and where the interaction model breaks down. Design changes are driven by lived experience, not speculation.

### Data Architecture Evaluation

The current flat-file approach (YAML + Markdown) optimizes for human readability and simplicity. As historical data accumulates, this may not scale well for the kind of pattern analysis and trend surfacing the system aspires to. A local indexed database (e.g., SQLite) could enable richer agent-driven insights across weeks and months of data. The plan is to let real usage reveal the pain points before committing to a migration.

### Structured Tracking Data

Currently, skills write tracking data (check-in logs, `current.yaml`, weekly plans, and the upcoming `coverage.yaml` from `/family-edu`) as freeform files — the LLM decides the shape on each write. This works but is fragile across sessions: schema drift, inconsistent field names, missing data, and wasted tokens re-reading large files are all real risks as usage accumulates.

The education standards pipeline (`feature/family-edu`) proved a pattern that should generalize to all tracking data:

1. **Schema definitions** — explicit, validated structure for every data file the system writes. Not just conventions in the skill prompt, but schemas that can be checked programmatically. Applies to `current.yaml`, checkin logs, weekly plans, and `coverage.yaml`.
2. **Validation on write** — after any skill writes or updates tracking data, validate against the schema before the session ends. Catches drift immediately instead of compounding across sessions.
3. **Summaries for efficient reads** — auto-generated summary files (like `summary.md` for standards) that give skills a quick snapshot without reading full data files. Regenerated after each validated write. Reduces token cost and improves reliability.

This is a cross-cutting concern that touches all skills, not just `/family-edu`. The approach:
- Define schemas (likely as Python dataclasses or YAML schema specs, reusing the `ingest-standards` validation pattern)
- Add a shared validation step that any skill can invoke post-write
- Generate summary snapshots per data domain (education, household state, weekly plan)
- Migrate existing data files to conform, updating skills as we go

**Relationship to DB evaluation**: This is a stepping stone. Structured, validated flat files are easier to migrate to a database later — the schema is already defined, validation is proven, and the summary layer maps naturally to materialized views.

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

