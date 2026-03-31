# ingest-standards

Ingests Indiana Academic Standards from public sources, validates across sources, and emits structured YAML files.

See [DESIGN-EDU-STANDARDS.md](../../DESIGN-EDU-STANDARDS.md) for architecture and [PLAN-EDU-STANDARDS.md](../../PLAN-EDU-STANDARDS.md) for implementation status.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```sh
cd scripts/ingest-standards
uv sync
```

## Commands

```sh
# Ingest Math K-5 from OpenSALT API → standards/indiana/
uv run ingest-standards ingest

# Validate all YAML files against the schema
uv run ingest-standards validate

# Print the extraction prompt for a subject (for Claude-assisted PDF parsing)
uv run ingest-standards prompt ela
uv run ingest-standards prompt science
uv run ingest-standards prompt social_studies
```

## PDF Extraction Workflow

ELA, Science, and Social Studies are extracted from IDOE PDFs using Claude. The prompts are stored in `src/ingest_standards/prompts/` for repeatability.

1. Download PDFs: `cache/` directory (gitignored)
2. Print the prompt: `uv run ingest-standards prompt <subject>`
3. Give Claude the prompt + PDF, collect the YAML output
4. Save to `standards/indiana/<subject>-<grade>.yaml`
5. Validate: `uv run ingest-standards validate`

The generated ELA/Science/Social Studies YAML files are gitignored (IDOE ToS restricts redistribution). Math YAML is committed (sourced from OpenSALT, no restrictions).

## Test

```sh
# Unit tests (30 tests)
uv run pytest -v

# Include live API integration tests (requires network)
LIVE_TESTS=1 uv run pytest -v

# Type checking
uv run ty check
```

## Dependencies

- **pyyaml** — YAML emission (only runtime dependency)
- **ty** — type checking (dev)
- **pytest** — testing (dev)

Everything else is Python stdlib.
