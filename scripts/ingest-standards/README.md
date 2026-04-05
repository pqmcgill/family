# ingest-standards

Ingests Indiana Academic Standards from public sources, validates across sources, and emits structured YAML files.

See [DESIGN-EDU-STANDARDS.md](../../project/DESIGN-EDU-STANDARDS.md) for architecture and [PLAN-EDU-STANDARDS.md](../../project/PLAN-EDU-STANDARDS.md) for implementation status.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```sh
cd scripts/ingest-standards
uv sync
```

## Full ETL

Math is ingested automatically from the OpenSALT API. ELA, Science, and Social Studies require Claude-assisted PDF extraction. Here's the complete pipeline:

### 1. Ingest Math (automated)

```sh
uv run ingest-standards ingest
```

Fetches Math K-5 from OpenSALT, validates, and writes YAML to `standards/indiana/`. This is committed to git (OpenSALT has no redistribution restrictions).

### 2. Download IDOE PDFs

```sh
mkdir -p cache
for grade in kindergarten grade-1 grade-2 grade-3 grade-4 grade-5; do
  for subject in english_language-arts science social-studies; do
    curl -sL -o "cache/${grade}-${subject}.pdf" \
      "https://media.doe.in.gov/standards/indiana-academic-standards-${grade}-${subject}.pdf"
    sleep 1  # courtesy delay
  done
done
```

Downloads 18 PDFs (~10MB total) into `cache/` (gitignored).

### 3. Extract standards from PDFs (Claude-assisted)

For each subject, print the extraction prompt and give it to Claude along with the PDF:

```sh
# Print the prompt for a subject
uv run ingest-standards prompt ela
uv run ingest-standards prompt science
uv run ingest-standards prompt social_studies
```

For each grade PDF:
1. Copy the prompt
2. Give Claude the prompt + the PDF file
3. Save the YAML output to `standards/indiana/<subject>-<grade>.yaml`

Repeat for all 18 files (6 grades × 3 subjects).

### 4. Validate

```sh
uv run ingest-standards validate
```

Checks all 24 YAML files against the schema: required fields, code patterns, essential flag hygiene, science NGSS dimensions, standard counts, and sub-standard structure. Exits non-zero if any file has errors.

### Output

The generated ELA/Science/Social Studies YAML files are gitignored (IDOE ToS restricts redistribution of derived data). Math YAML is committed (sourced from OpenSALT, no restrictions). Anyone cloning the repo can regenerate the full dataset by running the ETL above.

```
standards/indiana/
├── math-k.yaml through math-5.yaml       # committed (OpenSALT)
├── ela-k.yaml through ela-5.yaml         # gitignored (IDOE PDF)
├── science-k.yaml through science-5.yaml # gitignored (IDOE PDF)
├── social-studies-k.yaml through social-studies-5.yaml  # gitignored (IDOE PDF)
├── process-standards.yaml                 # committed (OpenSALT)
└── manifest.yaml                          # committed
```

## Commands Reference

```sh
uv run ingest-standards ingest [output_dir]       # Ingest math from OpenSALT
uv run ingest-standards validate [standards_dir]   # Validate YAML schema
uv run ingest-standards prompt <subject>           # Print PDF extraction prompt
```

## Test

```sh
uv run pytest -v               # Unit tests (30 tests)
LIVE_TESTS=1 uv run pytest -v  # Include live API integration tests
uv run ty check                # Type checking
```

## Dependencies

- **pyyaml** — YAML emission (only runtime dependency)
- **ty** — type checking (dev)
- **pytest** — testing (dev)

Everything else is Python stdlib.
