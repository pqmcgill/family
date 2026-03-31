# Social Studies Standards Extraction Prompt

Extract Indiana Academic Standards from this Social Studies PDF into YAML format.

## Output Format

```yaml
subject: social_studies
grade: {grade_label}
version: '2023'
source:
  primary: IDOE PDF
  primary_url: https://media.doe.in.gov/standards/indiana-academic-standards-{grade}-social-studies.pdf
  last_verified: '{today}'
standard_count: 0  # replace with actual count of leaf standards
domains:
  H:
    name: History
    learning_outcome: >
      [exact learning outcome text from the PDF]
    standards:
      {grade_label}.H.1:
        description: "[exact standard text, without (E) marker]"
        essential: true  # true if marked with (E), false otherwise
        examples: "[text after 'Examples:' if present]"
```

## Rules

1. **Standard codes**: `{grade_label}.{{domain}}.{{number}}` (e.g., K.H.1, 1.C.3, 2.G.2)
2. **Domains**: H (History), C (Civics and Government), G (Geography), E (Economics)
3. **Essential**: Standards marked with `(E)` → set `essential: true`, strip `(E)` from description
4. **Examples**: Some standards have `Examples:` bullets — capture as a single string in an `examples` field. Do NOT include examples in the description.
5. **Descriptions**: Copy EXACTLY from the PDF — do not paraphrase, summarize, or reword
6. **Learning outcomes**: Copy the full learning outcome statement that precedes each domain's standards
7. **standard_count**: Total number of leaf standards in the file
8. **Omit fields** that are not applicable (e.g., no `examples` field if the standard has no examples)

## Validation Checklist

Before returning, verify:
- [ ] All 4 domains are present (H, C, G, E)
- [ ] All standard codes follow the pattern `{grade_label}.{{H|C|G|E}}.{{number}}`
- [ ] Numbers are sequential within each domain (no gaps)
- [ ] `standard_count` matches the actual number of standards
- [ ] Essential markers match the (E) indicators in the PDF
- [ ] No standard description contains "(E)" — it should only be in the `essential` field
