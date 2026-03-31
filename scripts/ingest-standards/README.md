# ingest-standards

Ingests Indiana Academic Standards from public sources, validates across sources, and emits structured YAML files.

See [DESIGN-EDU-STANDARDS.md](../../DESIGN-EDU-STANDARDS.md) for architecture and [PLAN-EDU-STANDARDS.md](../../PLAN-EDU-STANDARDS.md) for implementation status.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```sh
cd scripts/ingest-standards
uv sync
```

## Run

```sh
# Ingest Math K-5 from OpenSALT → standards/indiana/
uv run ingest-standards

# Custom output directory
uv run ingest-standards /path/to/output
```

## Test

```sh
# Unit tests
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
