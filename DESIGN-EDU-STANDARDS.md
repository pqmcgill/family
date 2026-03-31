# Education Standards Ingestion — Technical Design

## Overview

This document describes the architecture for ingesting, structuring, validating, and serving Indiana Academic Standards data to the `/family-edu` skill. It covers the full pipeline from public government sources to the YAML files the agent reads at runtime.

For the skill's interaction model, data model, and behavioral requirements, see [REQUIREMENTS-EDU.md](REQUIREMENTS-EDU.md).

## Problem

The `/family-edu` skill needs a reliable, structured reference of Indiana Academic Standards to map activities to standards, track coverage, and surface gaps ([REQ: Standards Framework](REQUIREMENTS-EDU.md#standards-framework)). No single public source provides complete, current, machine-readable data for all subjects. The system must ingest from multiple sources, reconcile discrepancies, and produce validated YAML that the agent can trust.

## Design Principles

1. **PDFs are the authority.** IDOE PDFs are the canonical source for all Indiana standards. Structured APIs are productivity accelerators and validation cross-references, not sources of truth.
2. **Deterministic and rebuildable.** The ingestion pipeline is idempotent. Same inputs always produce the same output. YAML files can be regenerated from source at any time.
3. **Small corpus, no search infra.** K-2 is ~220 standards across 4 subjects. The full dataset fits in YAML files the agent reads directly. No embeddings, no vector DB, no search indexes.
4. **Adapters normalize, validators verify.** Source-specific parsing is isolated in adapters. Cross-source comparison is a separate validation step. The two concerns don't mix.
5. **Citation-first.** Standard codes (e.g., `K.NS.1`, `2.W.4a`, `1-PS4-1`) are the primary lookup mechanism. The LLM does the semantic matching between activities and standards.

## Source Landscape

Research conducted 2026-03-31. Standards refresh every 5-7 years per subject; annual check of IDOE site is sufficient.

### Available Sources

| Source | Format | Auth | License | Coverage | 2023 Data |
|--------|--------|------|---------|----------|-----------|
| **IDOE PDFs** | PDF | None | See note below | All subjects, all grades | Yes — all 4 core subjects |
| **OpenSALT API** | CASE JSON | None | MIT (software), public data | Limited — 3 IN frameworks via API | Math 2023 only (ELA/Science/SS visible on web UI but not in API) |
| **CSP API** | JSON | None | CC BY 3.0 (data from ASN) | All subjects, all grades | No — only 2014-2020 vintage |
| **ASN (D2L)** | JSON | Borrowed widget key | Unclear | Partial | ELA 2023 K-12; Math only 2020 for K-8 |

### Terms of Use and Rate Limits

Researched 2026-03-31.

**OpenSALT**: No ToS, no documented rate limits, no rate-limit headers in responses, robots.txt is empty. MIT-licensed open source software hosting public education standards data. No restrictions on data retrieval or redistribution found.

**CSP**: No ToS page. Apache 2.0 software, CC BY 3.0 licensed data (sourced from ASN — attribution to Desire2Learn Incorporated). No documented rate limits. Formally requires API key signup, but read endpoints work without one.

**IDOE PDFs**: The `media.doe.in.gov` robots.txt disallows all automated crawling (`Disallow: /`). The in.gov Terms of Use is restrictive boilerplate: "redistribution, use or publication...is strictly prohibited," with a carve-out for exceptions under Indiana law including the Access to Public Records Law. These are public education standards adopted by the State Board and published for use by every school, parent, and educator in Indiana. Our approach: download PDFs via direct URLs (not spidering), with courtesy delays, using an identifying User-Agent. For committed data, we prefer OpenSALT-sourced data (no restrictions) and note provenance clearly.

**Pipeline policy**: All HTTP requests include an identifying `User-Agent` header. Courtesy delays between requests. We make ~25 total API/download requests for a full K-5 ingestion — this is de minimis.

### Source URLs

**IDOE PDFs** — `https://media.doe.in.gov/standards/` and `https://www.in.gov/doe/files/`

Pattern: `indiana-academic-standards-{grade}-{subject}.pdf` where grade is `kindergarten` or `grade-N`.

**OpenSALT API** — `https://opensalt.net/ims/case/v1p0/`
- List frameworks: `GET /CFDocuments`
- Full package: `GET /CFPackages/{identifier}`
- Math 2023 identifier: `76673c2e-5cb6-11ee-a3bc-0242c0a84002`

**CSP API** — `http://api.commonstandardsproject.com/api/v1/`
- Indiana jurisdiction: `GET /jurisdictions/0F7091AB177F40D8B71B326CAFD13C8D`
- Standard set: `GET /standard_sets/{id}`

### Current Standards Versions

| Subject | Version | Est. Next Revision | Notes |
|---------|---------|-------------------|-------|
| Math | 2023 | ~2028-2030 | OpenSALT has structured 2023 data |
| ELA | 2023 | ~2028-2030 | PDF only for 2023 |
| Science | 2023 | ~2028-2030 | PDF only; NGSS-derived, most complex structure |
| Social Studies | 2023 | ~2028-2030 | PDF only |

## Standard Taxonomy

Standards vary significantly in structure across subjects. The data model must accommodate all four without forcing a single schema.

### ID Schemes

| Subject | Format | Examples | Hierarchy Depth |
|---------|--------|----------|-----------------|
| Math | `{grade}.{domain}.{number}` | `K.NS.1`, `2.CA.3` | 3 (Grade → Domain → Standard) |
| ELA | `{grade}.{domain}.{number}[{letter}]` | `2.RF.1`, `2.W.4a`, `2.W.7b.I` | 3-4 (Writing has sub-standards with letters, occasionally roman numerals) |
| Science | `{grade}-{discipline}{core_idea}-{number}` | `1-PS4-1`, `K-ESS3-1` | 3, but each standard bundles 4 dimensions |
| Social Studies | `{grade}.{domain}.{number}` | `2.H.3`, `K.E.1` | 3 (Grade → Domain → Standard) |

### Domains by Subject

**Math**: NS (Number Sense), CA (Computation & Algebraic Thinking), G (Geometry), M (Measurement), DA (Data Analysis)

**ELA**: RF (Reading Foundations), RC (Reading Comprehension), W (Writing), CC (Communication & Collaboration)

**Science**: PS (Physical Science), LS (Life Science), ESS (Earth & Space Science), ETS (Engineering/Technology — spans grade bands K-2, 3-5)

**Social Studies**: H (History), C (Civics & Government), G (Geography), E (Economics)

### Cross-Grade Elements

- **Math Process Standards** (PS.1-PS.8): Apply K-12. Not grade-specific. Stored separately.
- **Science & Engineering Practices** (SEP.1-SEP.8): Apply K-12. Each science standard references one.
- **Science Crosscutting Concepts** (CC.1-CC.7): Apply K-12. Each science standard references one.

### Grade Range

Per [REQUIREMENTS-EDU.md: Grade Range](REQUIREMENTS-EDU.md#grade-range):
- **Primary tracking: K-2.** Full ingestion with all metadata.
- **Awareness: 3-5.** Ingested for reference when activities hit above grade level. Same schema, same validation.
- **Not ingested: 6-12.** Can be added later if needed.

## Architecture

```
Ingestion Pipeline (run manually, ~once per standards revision cycle)
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ OpenSALT     │  │ PDF          │  │ CSP          │          │
│  │ Adapter      │  │ Adapter      │  │ Adapter      │          │
│  │ (Math 2023)  │  │ (all subjs)  │  │ (cross-check)│          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
│         └────────┬────────┘──────────────────┘                  │
│                  ▼                                               │
│         ┌────────────────┐                                      │
│         │ Canonical Node │  (common in-memory representation)   │
│         └────────┬───────┘                                      │
│                  ▼                                               │
│         ┌────────────────┐                                      │
│         │ Cross-Source   │  (compare adapters, flag conflicts)  │
│         │ Validator      │                                      │
│         └────────┬───────┘                                      │
│                  ▼                                               │
│         ┌────────────────┐                                      │
│         │ YAML Emitter   │  (write validated data to files)    │
│         └────────────────┘                                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Adapters

Each adapter parses a specific source format and yields canonical nodes. Adapters are stateless — they take a source input and produce a stream of nodes.

**OpenSaltAdapter**
- Input: CASE JSON from OpenSALT API
- Parses: `CFItems` array, `humanCodingScheme` → standard code, `fullStatement` → description, `educationLevel` → grade, `CFItemType` → node type
- Hierarchy: derived from `CFAssociations` parent-child relationships
- Available for: Math 2023 (K-12)

**PdfAdapter**
- Input: Downloaded IDOE PDF files
- Parses: Text extraction → regex-based parsing of standard codes + descriptions
- Handles per-subject structural differences:
  - Math/Social Studies: flat code + description rows
  - ELA: tabular layout with sub-standard letters, occasional roman numerals
  - Science: multi-panel pages with performance expectation + SEP + DCI + CC per standard; clarification statements in brackets; essential flag as separate label
- Available for: All subjects, all grades (authoritative source)

**CspAdapter**
- Input: JSON from Common Standards Project API
- Parses: `statementNotation` → code, `description` → text, `depth`/`parentId` → hierarchy
- Available for: All subjects, but only 2014-2020 vintage (deprecated standards)
- Primary use: cross-check validation against 2020→2023 correlation guides, not primary ingestion

### Canonical Node

The common in-memory representation that all adapters produce. Inspired by the KnowledgeNode pattern — a normalized unit with identity, content, source provenance, and subject-specific extensions.

```typescript
interface StandardNode {
  // Identity
  id: string;                    // e.g., "K.NS.1", "2.W.4a", "1-PS4-1"
  subject: Subject;              // "math" | "ela" | "science" | "social_studies"
  grade: string;                 // "K" | "1" | "2" | "3" | "4" | "5"
  domain: string;                // "NS", "RF", "PS4", "H", etc.
  type: NodeType;                // "standard" | "domain" | "process" | "sub_standard"

  // Content
  description: string;           // full standard text
  essential: boolean;            // marked with (E) / "Essential" in source

  // Hierarchy
  parent_id?: string;            // e.g., "2.W.4" for sub-standard "2.W.4a"
  children?: string[];           // child standard IDs

  // Source provenance
  source: {
    adapter: string;             // "opensalt" | "pdf" | "csp"
    url: string;                 // source URL
    version: string;             // "2023"
    retrieved: string;           // ISO date
  };

  // Subject-specific extensions
  extensions?: {
    // ELA
    sub_domain?: string;         // e.g., "Decoding" under Reading Foundations

    // Science (NGSS dimensions)
    clarification?: string;      // [Clarification Statement: ...]
    practice?: string;           // e.g., "SEP.3"
    practice_name?: string;      // "Planning and Carrying Out Investigations"
    core_idea?: string;          // e.g., "PS4.A"
    core_idea_name?: string;     // "Wave Properties"
    crosscutting?: string;       // e.g., "CC.2"
    crosscutting_name?: string;  // "Cause and Effect"
    boundary?: string;           // scope boundary statements
  };
}
```

### Cross-Source Validator

Runs after adapters produce nodes. Compares output from multiple adapters for the same subject/grade and flags discrepancies. Produces a validation report before any YAML is written.

**Checks:**

| Check | Description | Severity |
|-------|-------------|----------|
| **Count match** | Same number of standards per grade/domain across sources | Error |
| **Code match** | Same standard codes present in both sources | Error |
| **Code sequence** | Codes are sequential within each domain (no gaps) | Warning |
| **Text similarity** | Description text is substantially similar (fuzzy match) | Warning |
| **Essential flag** | Essential marking is consistent across sources | Warning |
| **Domain coverage** | All expected domains present for the grade | Error |
| **Hierarchy consistency** | Parent-child relationships are valid (parent exists, no orphans) | Error |

For Math (where both OpenSALT and PDF data are available), this is a full cross-source comparison. For ELA, Science, and Social Studies (PDF only), validation is structural — code format, sequencing, domain coverage, and hierarchy checks.

**Output:** A validation report (printed to console) listing all checks passed/failed, with details on any discrepancies. The pipeline does not write YAML if any Error-severity checks fail.

## Storage

The standards reference data and ingestion tooling are **public** (checked into git) — this is public domain government data and open-source tooling. The family's *usage* of that data (coverage tracking, activity logs, baseline assessments) is **private** (gitignored). This split updates the original layout in [REQUIREMENTS-EDU.md: Storage](REQUIREMENTS-EDU.md#storage).

```
# Public — checked into git
standards/                          # Parsed reference data (output of ingestion pipeline)
├── indiana/                        # State-specific (supports other states later)
│   ├── manifest.yaml               # Source versions, verification dates, counts
│   ├── summary.md                  # Condensed prompt context for agent
│   ├── math-k.yaml
│   ├── math-1.yaml
│   ├── math-2.yaml
│   ├── math-3.yaml                 # 3-5 for awareness
│   ├── math-4.yaml
│   ├── math-5.yaml
│   ├── ela-k.yaml
│   ├── ela-1.yaml
│   ├── ela-2.yaml
│   ├── ela-3.yaml
│   ├── ela-4.yaml
│   ├── ela-5.yaml
│   ├── science-k.yaml
│   ├── science-1.yaml
│   ├── science-2.yaml
│   ├── science-3.yaml
│   ├── science-4.yaml
│   ├── science-5.yaml
│   ├── social-studies-k.yaml
│   ├── social-studies-1.yaml
│   ├── social-studies-2.yaml
│   ├── social-studies-3.yaml
│   ├── social-studies-4.yaml
│   ├── social-studies-5.yaml
│   └── process-standards.yaml      # Math PS.1-8 and Science SEP.1-8, CC.1-7
│
scripts/                            # Ingestion pipeline tooling
├── ingest-standards/
│   ├── adapters/                   # Source-specific parsers
│   │   ├── opensalt.py             # (or .ts — TBD)
│   │   ├── pdf.py
│   │   └── csp.py
│   ├── validator.py                # Cross-source validation
│   ├── emitter.py                  # Canonical node → YAML
│   └── ingest.py                   # CLI entry point

# Private — gitignored (in data/)
data/edu/
├── coverage.yaml                   # Standards coverage state (REQ: Coverage Tracking)
└── activity-log/                   # Logged activities (REQ: Activity Log)
    └── YYYY-MM-DD.md
```

The `standards/` directory is committed because:
- The data is public domain (Indiana government publications)
- Other homeschool families could use the parsed data directly
- The ingestion pipeline is verifiable — anyone can re-run it and diff the output
- It enables code review of standards data changes when a new revision is adopted

Per [REQUIREMENTS-EDU.md: Key Principles](REQUIREMENTS-EDU.md#key-principles), all child-specific data stays in `data/` which is gitignored. The standards reference files contain no personal information — only government-published academic standards.

### YAML File Format

Each standards file has a consistent structure with a metadata header and nested content:

```yaml
# math-k.yaml
subject: math
grade: K
version: "2023"
source:
  primary: "IDOE PDF"
  primary_url: "https://media.doe.in.gov/standards/indiana-academic-standards-kindergarten-mathematics.pdf"
  verified_against: "OpenSALT"
  opensalt_id: "76673c2e-5cb6-11ee-a3bc-0242c0a84002"
  last_verified: "2026-03-31"
  standard_count: 15  # total leaf standards in this file

domains:
  NS:
    name: "Number Sense"
    learning_outcome: >
      Students build understanding of the number system,
      number sense, and place value concepts.
    standards:
      K.NS.1:
        description: "Count to at least 100 by ones and tens. Count by one from any given number."
        essential: true
      K.NS.2:
        description: "Write whole numbers from 0 to 20 and identify number words from 0 to 10. Represent a number of objects with a written numeral 0-20."
        essential: false
      # ...

  CA:
    name: "Computation and Algebraic Thinking"
    learning_outcome: "..."
    standards:
      K.CA.1:
        description: "..."
        essential: true
      # ...
```

Science files include the NGSS dimensions:

```yaml
# science-1.yaml
subject: science
grade: 1
version: "2023"
source:
  primary: "IDOE PDF"
  primary_url: "https://media.doe.in.gov/standards/indiana-academic-standards-grade-1-science.pdf"
  last_verified: "2026-03-31"
  standard_count: 12

domains:
  PS4:
    name: "Waves and Their Applications in Technologies for Information Transfer"
    standards:
      1-PS4-1:
        description: "Plan and conduct investigations to provide evidence that vibrating materials can make sound and that sound can make materials vibrate."
        clarification: "Examples of vibrating materials that make sound could include tuning forks and plucking a stretched string."
        essential: true
        practice: "SEP.3"
        core_idea: "PS4.A"
        crosscutting: "CC.2"
      # ...
```

ELA files handle sub-standards:

```yaml
# ela-2.yaml
subject: ela
grade: 2
version: "2023"
# ...

domains:
  W:
    name: "Writing"
    learning_outcome: >
      Students produce writing for a variety of purposes,
      applying their knowledge of language and sentence structure.
    standards:
      2.W.4:
        description: "Write narratives that:"
        essential: true  # (E) on sub-item d
        sub_standards:
          2.W.4a:
            description: "Include a beginning;"
          2.W.4b:
            description: "Use temporal words to signal event order (e.g., first of all);"
          2.W.4c:
            description: "Provide details to describe actions, thoughts, and feelings; and"
          2.W.4d:
            description: "Provide a middle and an ending."
```

### Manifest

Tracks pipeline provenance — when data was ingested, from what sources, with what results.

```yaml
# manifest.yaml
schema_version: 1
last_ingestion: "2026-03-31"
pipeline_version: "1.0.0"

sources_used:
  opensalt:
    url: "https://opensalt.net/ims/case/v1p0/"
    frameworks_fetched:
      - id: "76673c2e-5cb6-11ee-a3bc-0242c0a84002"
        title: "Indiana Academic Standards for Mathematics (2023)"
        item_count: 366
  idoe_pdf:
    base_url: "https://media.doe.in.gov/standards/"
    files_processed: 24  # K-5 × 4 subjects

validation_results:
  math:
    cross_source_check: "pass"  # OpenSALT vs PDF
    sources_compared: ["opensalt", "pdf"]
  ela:
    structural_check: "pass"
    sources_compared: ["pdf"]
  science:
    structural_check: "pass"
    sources_compared: ["pdf"]
  social_studies:
    structural_check: "pass"
    sources_compared: ["pdf"]

standard_counts:
  math: { K: 15, 1: 15, 2: 20, 3: 24, 4: 25, 5: 23 }
  ela: { K: 24, 1: 26, 2: 24, 3: 26, 4: 24, 5: 23 }
  science: { K: 13, 1: 12, 2: 14, 3: 18, 4: 17, 5: 16 }
  social_studies: { K: 14, 1: 21, 2: 23, 3: 29, 4: 37, 5: 40 }
```

### Summary (Agent Prompt Context)

A `summary.md` file provides condensed context injected into the `/family-edu` skill's system prompt. This gives the agent baseline awareness of what standards exist without needing to read every YAML file.

Content includes:
- Domains per subject with standard count ranges
- Grade-level highlights (what's new at each grade vs. prior)
- Which standards are marked essential
- Cross-grade process standards (Math PS, Science SEP/CC)
- Known structural quirks (ELA sub-standards, Science grade-band ETS)

Target size: under 2,000 tokens. The agent reads individual YAML files on demand for full standard text.

## Agent Integration

At `/family-edu` runtime, the agent accesses standards data through direct file reads, not a search layer.

### Lookup Patterns

**By code** (citation-first): User or agent references `2.NS.1` → read `standards/indiana/math-2.yaml`, navigate to `domains.NS.standards.2.NS.1`.

**By domain**: "What 2nd grade geometry standards exist?" → read `standards/indiana/math-2.yaml`, list all standards under `domains.G`.

**By grade**: "Where are we in 1st grade?" → read all `standards/indiana/*-1.yaml` files, cross-reference with `data/edu/coverage.yaml`.

**Activity mapping**: "We built a birdhouse" → agent reads `summary.md` (already in prompt) to identify likely domains (science: engineering/ETS, math: measurement/geometry), then reads those specific YAML files to find matching standards. The LLM is the semantic matcher.

### Coverage Integration

Per [REQUIREMENTS-EDU.md: Coverage Tracking](REQUIREMENTS-EDU.md#coverage-tracking), the `coverage.yaml` file references standards by their canonical IDs:

```yaml
standards:
  K.NS.1:
    status: mastered
    last_touched: "2026-02-15"
    source: baseline
    activities: []
    notes: "Wife confirmed during baseline session"
  2.W.4:
    status: practiced
    last_touched: "2026-03-20"
    source: activity
    activities: ["2026-03-20-story-writing"]
```

This separation — reference data in `standards/indiana/` (public, committed), tracking state in `data/edu/coverage.yaml` (private, gitignored) — means the ingestion pipeline never touches coverage data, and coverage never drifts from the canonical standard IDs.

## Refresh Strategy

Standards revisions are infrequent (5-7 year cycles per subject) and announced well in advance (6-12 month process from announcement to adoption).

**Annual check**: Visit `https://www.in.gov/doe/students/indiana-academic-standards/` and `https://www.in.gov/sboe/meetings/` once per year (e.g., during summer planning) to check for announced revisions.

**When a revision is adopted**:
1. Download new IDOE PDFs
2. Check if OpenSALT/CSP have updated (may lag by months)
3. Re-run ingestion pipeline
4. Review validation report
5. Diff new YAML against old to understand what changed
6. Update `coverage.yaml` — map old standard IDs to new ones using IDOE's published correlation guides

**Monitoring URLs**:
- IDOE Standards: `https://www.in.gov/doe/students/indiana-academic-standards/`
- State Board meetings: `https://www.in.gov/sboe/meetings/`

## Open Questions

These need resolution before or during implementation:

1. **PDF parsing approach**: Claude can read PDFs directly. Should the "PdfAdapter" be a Claude-assisted extraction (download PDF, have Claude read it and output structured YAML, validate the output), or a traditional text-extraction pipeline (pdftotext → regex)? The former is simpler and handles layout variation better; the latter is more deterministic.

2. **ELA sub-standard granularity**: `2.W.7` has sub-items `a-d`, and `2.W.7b` further splits into roman numerals `I` and `II`. Should these be tracked as individual standards in coverage, or should tracking stop at the letter level? ([REQ: Open Questions — Granularity](REQUIREMENTS-EDU.md#open-questions))

3. **Science dimension tracking**: Each science standard bundles a practice (SEP), core idea (DCI), and crosscutting concept (CC). Should coverage track just the performance expectation, or also track which practices/concepts have been exercised? The latter gives richer insight but adds complexity.

4. **3-5 ingestion timing**: The requirements say "awareness of 3-5" — ingest now with the same pipeline, or defer until the K-2 pipeline is proven? Ingesting now is marginal extra work and enables the "that was 4th grade level!" celebration use case immediately.
