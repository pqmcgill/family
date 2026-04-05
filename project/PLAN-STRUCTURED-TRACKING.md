# Plan: Semantic Search for Family Data

## Context

As data accumulates across weeks, skills can't reliably surface all relevant context — forgotten TODOs, stale radar items, missed patterns — because they'd need to read every historical file. Vector search over all historical data lets skills query for what's relevant instead of reading everything.

## Architecture

```
Skills write flat files (YAML/MD) as they do today
  → Indexer chunks & embeds into LanceDB after each write
  → Skills query vector store for context before generating insights
  → Flat files remain human-readable source of truth
  → Vector store is a derived index, rebuildable from files
```

## Implementation

### Phase 0: Organize project docs

Move project planning documents from repo root into `project/`:
- `ROADMAP.md` → `project/ROADMAP.md`
- `REQUIREMENTS.md` → `project/REQUIREMENTS.md`
- `REQUIREMENTS-EDU.md` → `project/REQUIREMENTS-EDU.md`
- `DESIGN-EDU-STANDARDS.md` → `project/DESIGN-EDU-STANDARDS.md`
- `PLAN-EDU-STANDARDS.md` → `project/PLAN-EDU-STANDARDS.md`

Move this plan file there too: → `project/PLAN-STRUCTURED-TRACKING.md`

Update references to moved files:
- `CLAUDE.md` — `REQUIREMENTS.md` → `project/REQUIREMENTS.md`
- `.claude/commands/family-checkin.md` — `REQUIREMENTS.md` → `project/REQUIREMENTS.md`
- `.claude/commands/family-plan.md` — `REQUIREMENTS.md` → `project/REQUIREMENTS.md`
- `.claude/commands/family-init.md` — `REQUIREMENTS.md` → `project/REQUIREMENTS.md` (2 references)
- `.claude/commands/family-edu.md` — `REQUIREMENTS-EDU.md` → `project/REQUIREMENTS-EDU.md`
- `scripts/ingest-standards/README.md` — update relative paths to `DESIGN-EDU-STANDARDS.md` and `PLAN-EDU-STANDARDS.md`
- Cross-references within the project docs themselves (DESIGN→REQUIREMENTS-EDU, PLAN→DESIGN, ROADMAP→REQUIREMENTS-EDU/DESIGN) become relative links within `project/` — simpler paths

### Phase 1: Vector store package

**New package: `scripts/vector-store/`** (same pattern as `scripts/ingest-standards/`)

Dependencies: `lancedb`, `sentence-transformers`, `pyyaml`

CLI commands:
- `vector-store index <file-or-dir>` — chunk and embed into the store
- `vector-store search <query> [--limit N] [--filter type=checkin]` — semantic search, returns relevant chunks
- `vector-store rebuild` — re-index everything from flat files
- `vector-store status` — show what's indexed

Storage: `data/vector_store/` (gitignored)

**Chunking strategy:**
- Checkin logs → one chunk per domain section (tagged with date, domain, type=checkin)
- Weekly plans → separate chunks for caregiver checklist vs partner insights
- current.yaml → one chunk per top-level key (last_done, laundry, one_offs, radar)
- Edu coverage → one chunk per standard
- Activity logs → one chunk per activity entry

Each chunk gets metadata: `{source_file, date, type, domain}` for filtered search.

**Files:**
- `scripts/vector-store/pyproject.toml`
- `scripts/vector-store/src/vector_store/__init__.py`
- `scripts/vector-store/src/vector_store/cli.py`
- `scripts/vector-store/src/vector_store/chunker.py`
- `scripts/vector-store/src/vector_store/store.py`

### Phase 2: Initial index

- Add `data/vector_store/` to `.gitignore`
- Run `vector-store rebuild` to index all existing data

### Phase 3: Skill updates

Update each skill to:
1. **Query vector store** for context before generating output
2. **Index new data** after writing

Priority order:
- `family-checkin.md` — query for open tasks, recent patterns; index checkin log after write
- `family-status.md` — query vector store instead of reading all historical files
- `family-plan.md` — query for multi-week patterns, forgotten items; index plan after write
- `family-log.md` — index after write
- `family-edu.md` — query for coverage patterns; index after write

### Phase 4: Documentation

Update `CLAUDE.md` with vector store usage (how to index, query, rebuild).

## Verification

- `vector-store rebuild` — indexes all existing data without errors
- `vector-store search "open tasks"` — returns relevant one_offs
- `vector-store search "homeschool this week"` — returns recent checkin entries
- Run `/family-status` — produces richer output using vector context
- Run `/family-checkin` — indexes new data after write
