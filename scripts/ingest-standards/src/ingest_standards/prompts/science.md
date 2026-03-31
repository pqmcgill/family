# Science Standards Extraction Prompt

Extract Indiana Academic Standards from this Science PDF into YAML format.

Science uses the NGSS 3-dimensional framework. Each standard bundles a Performance Expectation with three dimensions (Practice, Core Idea, Crosscutting Concept).

## Output Format

```yaml
subject: science
grade: {grade_label}
version: '2023'
source:
  primary: IDOE PDF
  primary_url: https://media.doe.in.gov/standards/indiana-academic-standards-{grade}-science.pdf
  last_verified: '{today}'
standard_count: 0  # replace with actual count of performance expectations
domains:
  PS4:
    name: "Waves and Their Applications in Technologies for Information Transfer"
    standards:
      1-PS4-1:
        description: "[Performance Expectation text — the bold statement]"
        essential: true
        clarification: "[text from Clarification Statement brackets, if present]"
        boundary: "[text from Boundary statement, if present]"
        practice: "SEP.3"
        core_idea: "PS4.A"
        crosscutting: "CC.2"
```

## Rules

1. **Standard codes use HYPHENS**: `{{grade}}-{{discipline}}{{coreIdea}}-{{number}}` (e.g., K-PS2-1, 1-LS1-2, 2-ESS1-1). NOT dots.
2. **Domain keys**: Use the DCI group prefix: PS1, PS2, PS3, PS4, LS1, LS2, LS3, LS4, ESS1, ESS2, ESS3, ETS1
3. **Domain names**: Use the topic title shown in the dark header bar (e.g., "Waves and Their Applications in Technologies for Information Transfer")
4. **Essential**: Marked with "Essential" label in the PDF → `essential: true`
5. **Description**: The Performance Expectation (bold text). Copy EXACTLY.
6. **Clarification**: Text in `[Clarification Statement: ...]` brackets. Omit field if none.
7. **Boundary**: Text in `(Boundary: ...)` parentheses. Omit field if none.

## NGSS Dimension Codes

Map the practice name shown in the colored panel to its code:

| Practice | Code |
|----------|------|
| Asking Questions and Defining Problems | SEP.1 |
| Developing and Using Models | SEP.2 |
| Planning and Carrying Out Investigations | SEP.3 |
| Analyzing and Interpreting Data | SEP.4 |
| Using Mathematics and Computational Thinking | SEP.5 |
| Constructing Explanations and Designing Solutions | SEP.6 |
| Engaging in Argument from Evidence | SEP.7 |
| Obtaining, Evaluating, and Communicating Information | SEP.8 |

Map the crosscutting concept name to its code:

| Concept | Code |
|---------|------|
| Patterns | CC.1 |
| Cause and Effect | CC.2 |
| Scale, Proportion, and Quantity | CC.3 |
| Systems and System Models | CC.4 |
| Energy and Matter | CC.5 |
| Structure and Function | CC.6 |
| Stability and Change | CC.7 |

Use the DCI code shown in the panel header (e.g., "PS4.A: Wave Properties" → `core_idea: "PS4.A"`).

## Special Cases

- **ETS (Engineering)** standards may span grade bands: K-2-ETS1-1, 3-5-ETS1-1. Use the code exactly as shown.
- Group ETS standards under domain key `ETS1`.
- Some standards reference multiple DCIs — use the primary (first listed) one.

## Validation Checklist

Before returning, verify:
- [ ] All standard codes use hyphens, not dots
- [ ] Each standard has practice, core_idea, and crosscutting fields
- [ ] Practice codes are SEP.1-SEP.8
- [ ] Crosscutting codes are CC.1-CC.7
- [ ] `standard_count` matches actual number of performance expectations
- [ ] No description contains "[Clarification Statement" — that goes in `clarification`
- [ ] Essential flags match the "Essential" labels in the PDF
