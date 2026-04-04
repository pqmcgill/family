# Indiana Academic Standards — Agent Reference

2023 Indiana Academic Standards, K-5. This summary provides baseline context for the `/family-edu` skill. Read individual YAML files on demand for full standard text.

## File Layout

Standards are in `standards/indiana/{subject}-{grade}.yaml` (e.g., `math-k.yaml`, `ela-2.yaml`, `science-1.yaml`, `social-studies-3.yaml`). Cross-grade process standards are in `process-standards.yaml`.

## Math (122 standards K-5)

Five domains, consistent across all grades:

| Domain | Code | K | 1 | 2 | 3 | 4 | 5 |
|--------|------|---|---|---|---|---|---|
| Number Sense | NS | 7 | 4 | 5 | 6 | 7 | 4 |
| Computation & Algebraic Thinking | CA | 4 | 4 | 4 | 8 | 9 | 11 |
| Geometry | G | 1 | 3 | 4 | 3 | 3 | 1 |
| Measurement | M | 2 | 3 | 6 | 6 | 4 | 5 |
| Data Analysis | DA | 1 | 1 | 1 | 1 | 2 | 2 |

Standard codes: `{grade}.{domain}.{number}` (e.g., K.NS.1, 2.CA.3).

Eight cross-grade **Process Standards** (PS.1-PS.8) apply to all math work: problem-solving, reasoning, argumentation, modeling, tools, precision, structure, patterns.

## ELA (283 standards K-5)

Four domains:

| Domain | Code | K | 1 | 2 | 3 | 4 | 5 |
|--------|------|---|---|---|---|---|---|
| Reading Foundations | RF | 9 | 8 | 4 | 5 | 3 | 2 |
| Reading Comprehension | RC | 7 | 10 | 12 | 13 | 13 | 14 |
| Writing | W | 15 | 17 | 19 | 29 | 32 | 30 |
| Communication & Collaboration | CC | 5 | 7 | 7 | 8 | 7 | 7 |

Standard codes: `{grade}.{domain}.{number}` (e.g., 2.RF.1, K.RC.3).

**Structural notes:**
- RF has sub-domains in K-2: Print Concepts, Phonological/Phonemic Awareness, Decoding. These are in the `sub_domain` field.
- Writing standards frequently have **sub-standards** with letter suffixes (e.g., 2.W.4a, 2.W.4b). The W counts above include these sub-standards.
- RF shrinks as grades increase (foundational skills mastered); RC and W grow.

## Science (89 standards K-5)

NGSS-derived. Domains vary by grade — not every discipline appears at every level.

| Discipline | Grades Present |
|------------|---------------|
| Physical Science (PS1-PS4) | Every grade, different topics |
| Life Science (LS1-LS4) | Every grade, different topics |
| Earth & Space Science (ESS1-ESS3) | Every grade, different topics |
| Engineering/Technology (ETS1) | Every grade (K-2 and 3-5 grade bands) |

Standard codes use **hyphens**: `{grade}-{discipline}{coreIdea}-{number}` (e.g., 1-PS4-1, K-ESS3-2, 3-5-ETS1-1).

**Each science standard bundles four components:**
- `description`: The Performance Expectation (what students demonstrate)
- `practice`: Science & Engineering Practice code (SEP.1-SEP.8)
- `core_idea`: Disciplinary Core Idea code (e.g., PS4.A, LS1.B)
- `crosscutting`: Crosscutting Concept code (CC.1-CC.7)
- `clarification`: Examples and scope (optional)
- `boundary`: Scope limitations (optional)

ETS standards span grade bands (K-2-ETS1-1, 3-5-ETS1-1) rather than individual grades.

## Social Studies (164 standards K-5)

Four domains, consistent across all grades:

| Domain | Code | K | 1 | 2 | 3 | 4 | 5 |
|--------|------|---|---|---|---|---|---|
| History | H | 4 | 8 | 7 | 8 | 15 | 18 |
| Civics & Government | C | 2 | 5 | 5 | 5 | 6 | 8 |
| Geography | G | 5 | 5 | 6 | 8 | 9 | 8 |
| Economics | E | 3 | 3 | 5 | 8 | 7 | 6 |

Standard codes: `{grade}.{domain}.{number}` (e.g., K.H.1, 2.G.3, 5.C.7).

History grows significantly in upper grades (Indiana/US history). Some standards include `examples` with illustrative activities.

## Essential Standards

Standards marked `essential: true` are identified by IDOE as essential for mastery by grade-level end. Roughly 60% of math standards and varying proportions of other subjects are essential. Non-essential standards are still required to be taught — the essential flag indicates prioritization.

## How to Look Up Standards

1. Identify subject and grade from context
2. Read `standards/indiana/{subject}-{grade}.yaml`
3. Navigate to the relevant domain, then find the standard by code
4. For coverage tracking, cross-reference with `data/edu/coverage.yaml`
