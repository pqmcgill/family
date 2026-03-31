# Education Standards — Implementation Plan

Execution plan for [DESIGN-EDU-STANDARDS.md](DESIGN-EDU-STANDARDS.md). Each phase produces a usable artifact and can be paused without losing progress.

## Decision: Resolve Open Questions First

These from the design doc need answers before writing code.

### 1. PDF parsing approach

**Decision: Claude-assisted extraction.**

Rationale: The IDOE PDFs have complex, variable layouts (science is multi-panel, ELA is tabular with sub-items, math is flat). A regex pipeline would need per-subject parsers that are brittle to layout changes. Claude can read the PDFs directly and output structured YAML — the same model that will *use* the data can *parse* it. The validation layer catches errors regardless of how the parsing is done.

Workflow: Download PDF → Claude reads it → outputs YAML per the schema → validator checks the output → human reviews the diff. The "adapter" for PDFs is really a prompt + validation check, not a code module.

Trade-off: Not deterministic in the traditional sense — running twice might produce slightly different whitespace or description phrasing. Mitigated by: committing the output (so the YAML is the artifact, not the process), and validation catches structural issues.

### 2. ELA sub-standard granularity

**Decision: Track at the letter level, not roman numerals.**

`2.W.4a` through `2.W.4d` are individually trackable. `2.W.7b.I` and `2.W.7b.II` are captured in the YAML for reference but coverage tracks at `2.W.7b`. This keeps the tracking surface manageable while preserving the full standard text. Can revisit if the caregiver wants finer grain.

### 3. Science dimension tracking

**Decision: Track performance expectations only. Tag dimensions for reference.**

Coverage tracks `1-PS4-1`, not `SEP.3` or `CC.2` individually. But the YAML stores which SEP/DCI/CC each standard exercises, so the agent can observe patterns like "you've been heavy on SEP.3 (investigations) but haven't done much SEP.2 (modeling)." This is an insight the agent surfaces conversationally, not a formal tracking axis.

### 4. 3-5 ingestion timing

**Decision: Ingest K-5 together from the start.**

Same pipeline, same schema, marginal extra effort. Enables the celebration use case ("that was 4th grade level!") from day one. No reason to defer.

---

## Phase 1: Math via OpenSALT (Structured Source)

**Goal**: End-to-end pipeline proven on the easiest path — structured API data, single subject, full K-5.

### 1a. Scaffold project structure

Create the directory layout and empty files:

```
standards/
└── indiana/

scripts/
└── ingest-standards/
    ├── adapters/
    ├── models.py          # StandardNode dataclass
    ├── validator.py
    ├── emitter.py
    └── ingest.py
```

Choose Python (stdlib only — `urllib`, `json`, `yaml` via a single dependency or hand-rolled emitter). Zero supply chain surface is a goal; if we need a YAML library, `pyyaml` is the one dependency we'd accept.

### 1b. StandardNode model + YAML emitter

Implement the canonical `StandardNode` dataclass from the design doc. Write the YAML emitter that takes a list of nodes and produces the per-grade file format. Test with hand-crafted nodes before any adapter exists.

**Deliverable**: Can create a `math-k.yaml` from code with the correct schema.

### 1c. OpenSALT adapter

Fetch the Math 2023 package (`76673c2e-5cb6-11ee-a3bc-0242c0a84002`) from the CASE API. Parse `CFItems` and `CFAssociations` into `StandardNode` objects. Handle:
- Process standards (PS.1-8) → separate file
- Grade filtering (extract K-5 items by `educationLevel`)
- Domain grouping (NS, CA, G, M, DA)
- Essential flag (from `notes` field containing "(E)")
- Hierarchy (items with `CFItemType` = "Standard" vs. "Strand" vs. organizational)

**Deliverable**: `standards/indiana/math-k.yaml` through `math-5.yaml` + `process-standards.yaml` generated from live API data.

### 1d. Structural validator (single-source mode)

Implement the validation checks that work with a single source (no cross-source comparison yet):
- Code format regex per subject
- Sequential numbering within domains (no gaps)
- Domain coverage (all expected domains present)
- Hierarchy consistency (parents exist, no orphans)
- Essential flag presence
- Standard count sanity check

Run against the OpenSALT-generated math files.

**Deliverable**: Validator runs, reports pass/fail, blocks YAML output on errors.

### 1e. Manifest generation

After successful validation, generate `manifest.yaml` with source metadata, standard counts, and validation results.

**Deliverable**: `standards/indiana/manifest.yaml` populated for math.

### Phase 1 checkpoint

At this point we have: 6 math YAML files (K-5) + process standards + manifest, all generated from OpenSALT, structurally validated, committed to git. The pipeline works end-to-end for one subject from one source.

---

## Phase 2: Math Cross-Validation (PDF vs. API)

**Goal**: Prove the cross-source validation layer using math, where we have both structured API data and the authoritative PDF.

### 2a. PDF adapter for math

Download the K-5 math PDFs from IDOE. Use Claude-assisted extraction:
1. Read each PDF
2. Prompt Claude to extract standards in a specified JSON structure
3. Parse the JSON into `StandardNode` objects
4. The "adapter" is a script that orchestrates this: download → Claude extraction → node creation

Store downloaded PDFs in a `cache/` directory (gitignored) so re-runs don't re-download.

**Deliverable**: Math K-5 `StandardNode` lists from PDF source, alongside the existing OpenSALT nodes.

### 2b. Cross-source validator

Extend the validator with cross-source comparison checks:
- Count match per grade per domain
- Code match (same standard IDs in both sources)
- Text similarity (fuzzy — descriptions may differ slightly between PDF and API wording)
- Essential flag consistency

Output a comparison report: what matches, what differs, which source to trust for each discrepancy.

**Deliverable**: Validation report for Math K-5 showing OpenSALT vs. PDF agreement. Any discrepancies documented and resolved (PDF wins as the authority).

### 2c. Merge strategy

When both sources agree: use the data as-is.
When they disagree: use PDF text (authoritative), note the discrepancy in the manifest.
When one source has data the other doesn't: include it, flag the source.

Update the math YAML files if the PDF reveals corrections to the OpenSALT data.

**Deliverable**: Final math YAML files with `verified_against: "OpenSALT"` in the source metadata.

### Phase 2 checkpoint

Math is fully validated across two independent sources. The cross-source validator is proven. We now know how accurate the OpenSALT data is relative to the PDFs — this calibrates our trust for future use.

---

## Phase 3: Remaining Subjects (PDF-Only)

**Goal**: Ingest ELA, Science, and Social Studies from PDFs. No structured API source exists for these in 2023 vintage.

### 3a. ELA ingestion

Claude-assisted PDF extraction for K-5 ELA. This is the medium-complexity case:
- 4 domains (RF, RC, W, CC)
- Sub-standards with letters under Writing
- Occasional roman numeral sub-items (captured in YAML, tracked at letter level per decision above)
- Learning outcome statements per domain

Run structural validator. Review output manually against rendered PDFs for a handful of grades.

**Deliverable**: `ela-k.yaml` through `ela-5.yaml` committed.

### 3b. Science ingestion

Claude-assisted PDF extraction for K-5 Science. The hardest case:
- NGSS-style coding (`1-PS4-1`)
- Multi-panel layout: performance expectation + SEP + DCI + CC per standard
- Clarification statements and boundary statements
- Essential flag as a separate label, not inline `(E)`
- ETS standards that span grade bands (K-2, 3-5) — assign to the grade band, not individual grades

Run structural validator. Pay special attention to:
- Correct parsing of the 4 NGSS dimensions per standard
- ETS grade-band handling
- No conflation of clarification text with description text

**Deliverable**: `science-k.yaml` through `science-5.yaml` committed. Process standards file updated with SEP.1-8 and CC.1-7.

### 3c. Social Studies ingestion

Claude-assisted PDF extraction for K-5 Social Studies. Expected to be straightforward (flat like math):
- 4 domains (H, C, G, E)
- Dot-notation codes (`2.H.3`)
- No sub-standards expected

Run structural validator.

**Deliverable**: `social-studies-k.yaml` through `social-studies-5.yaml` committed.

### 3d. Full manifest and final validation

Update manifest with all 4 subjects. Run a full cross-subject sanity check:
- Total standard counts per grade match expectations from research
- All domains present across all grades
- No duplicate standard IDs across files
- Process standards referenced by science nodes actually exist in the process standards file

**Deliverable**: Complete `manifest.yaml`. All 24 YAML files (4 subjects × 6 grades) + process standards committed and validated.

### Phase 3 checkpoint

The full K-5 Indiana Academic Standards reference dataset is complete, validated, and committed. This is the artifact that is useful to anyone — the public, reusable part of the project.

---

## Phase 4: Agent Context Layer

**Goal**: Produce the `summary.md` that gives the agent baseline awareness, and verify the data works in practice.

### 4a. Generate summary.md

Write the condensed prompt context file. Content:
- Subject overview (4 subjects, their domains, standard count ranges by grade)
- What "essential" means and how it's marked
- Key structural notes (ELA sub-standards, science NGSS dimensions, grade-band ETS)
- Cross-grade process standards summary
- How to look up a specific standard (file naming convention, YAML structure)

Target: under 2,000 tokens. This is what goes into the `/family-edu` skill's system prompt.

**Deliverable**: `standards/indiana/summary.md` committed.

### 4b. Smoke test with Claude

Before building the full skill, test the data layer manually:
- Start a Claude conversation with `summary.md` as context
- Try the core use cases from [REQUIREMENTS-EDU.md: Session Types](REQUIREMENTS-EDU.md#session-types):
  - "She built a tower out of blocks and sorted them by shape" → does the agent correctly identify geometry standards?
  - "What 2nd grade math standards haven't we covered?" → can the agent read the YAML and cross-reference a mock coverage file?
  - "What does K.NS.1 mean in practice?" → does the agent give a useful plain-language explanation?
- Note any issues with the YAML structure, summary completeness, or standard descriptions

**Deliverable**: Confidence that the data layer works for the agent's needs. List of any schema adjustments needed.

### Phase 4 checkpoint

The standards data is agent-ready. The summary provides sufficient context for the LLM to navigate the data. Ready to build the skill.

---

## Phase 5: /family-edu Skill

**Goal**: Build the conversational skill that uses the standards data. This is the family-specific layer.

### 5a. Skill prompt + coverage schema

Write the `/family-edu` skill definition (`.claude/commands/family-edu.md`). Define the `coverage.yaml` schema and the activity log format. The skill prompt should:
- Load `summary.md` as baseline context
- Check for `data/edu/coverage.yaml` existence (offer baseline setup if missing)
- Support the 4 session types from requirements: log activities, review coverage, build baseline, explore standards
- Follow the principles: wife is the expert, activities first, no implied mastery

**Deliverable**: Skill file committed. Coverage and activity log schemas documented.

### 5b. Baseline building flow

Implement the conversational flow for establishing initial coverage state:
- Walk through subjects one at a time
- Describe what each domain's standards cover in plain language
- Ask the caregiver where the child stands
- Record assessments as baseline entries in `coverage.yaml`

This is the first real use of the skill — it creates the initial `data/edu/coverage.yaml`.

**Deliverable**: Working baseline flow that populates coverage state.

### 5c. Activity logging flow

Implement the log-and-map flow:
- User describes activities naturally
- Agent maps to standards (reading YAML files for candidate matches)
- Presents mapping for confirmation
- Updates `coverage.yaml` and writes to `activity-log/`

**Deliverable**: Working activity logging that updates coverage state.

### 5d. Coverage review flow

Implement the gap analysis and coverage summary:
- Read all coverage state + standards reference
- Summarize by subject and domain
- Flag: not started, stale (configurable threshold), thin coverage
- For each gap, ask whether it's a real gap or just unlogged

**Deliverable**: Working coverage review with gap surfacing.

### Phase 5 checkpoint

The `/family-edu` skill is functional for all 4 session types. The family can start using it.

---

## Out of Scope (For Now)

- **Formal reporting** — generating reports for Indiana's annual homeschool assessment requirement. Deferred until we know if the family needs it. ([REQ: Open Questions — Reporting](REQUIREMENTS-EDU.md#open-questions))
- **Multiple children** — Kid 2 will eventually need tracking. The schema supports it (separate coverage files) but the skill doesn't yet. ([REQ: Not In Scope](REQUIREMENTS-EDU.md#not-in-scope-for-now))
- **Standalone repo split** — breaking standards data + pipeline into its own project. Deferred until the data and pipeline are stable.
- **Other states** — the `standards/indiana/` namespace supports it, but no plans to ingest other states.
