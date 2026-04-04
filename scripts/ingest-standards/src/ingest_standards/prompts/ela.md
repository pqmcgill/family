# ELA Standards Extraction Prompt

Extract Indiana Academic Standards from this English/Language Arts PDF into YAML format.

## Output Format

```yaml
subject: ela
grade: {grade_label}
version: '2023'
source:
  primary: IDOE PDF
  primary_url: https://media.doe.in.gov/standards/indiana-academic-standards-{grade}-english_language-arts.pdf
  last_verified: '{today}'
standard_count: 0  # replace with actual count of leaf standards (see counting rules below)
domains:
  RF:
    name: Reading Foundations
    learning_outcome: >
      [exact learning outcome text from the PDF]
    standards:
      {grade_label}.RF.1:
        description: "[exact standard text, without (E) marker]"
        essential: true
        sub_domain: "Decoding"  # if a sub-heading exists above this standard
```

## Sub-Standards

Some standards (especially in Writing) have lettered sub-items. Represent them as:

```yaml
      2.W.4:
        description: "Write narratives that:"
        essential: true  # (E) may appear on a sub-item — set on parent if any sub-item has it
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

If a sub-standard has **roman numeral** sub-items (e.g., 2.W.7b has I and II), fold them into the letter-level description. Do NOT create separate entries for roman numerals.

## Rules

1. **Standard codes**: `{grade_label}.{{domain}}.{{number}}` (e.g., K.RF.1, 2.RC.3, 3.W.5a)
2. **Domains**: RF (Reading Foundations), RC (Reading Comprehension), W (Writing), CC (Communication and Collaboration)
3. **Essential**: Standards marked with `(E)` → set `essential: true`, strip `(E)` from description. If `(E)` appears on a sub-item, set essential on the parent standard.
4. **Sub-domains**: Reading Foundations may have sub-headings (Print Concepts, Phonological Awareness, Phonemic Awareness, Decoding). Capture as `sub_domain` on relevant standards.
5. **Descriptions**: Copy EXACTLY from the PDF — do not paraphrase
6. **standard_count**: Count leaf standards. For standards WITH sub_standards, count each letter-level sub-standard as 1. For standards WITHOUT sub_standards, count the standard itself as 1.
7. **Omit fields** that are not applicable (no `sub_domain` if none exists, no `essential` if false)

## Validation Checklist

Before returning, verify:
- [ ] All 4 domains are present (RF, RC, W, CC)
- [ ] Standard codes follow `{grade_label}.{{RF|RC|W|CC}}.{{number}}[{{a-z}}]` pattern
- [ ] Numbers are sequential within each domain (no gaps)
- [ ] `standard_count` matches actual leaf count
- [ ] No description contains "(E)"
- [ ] Sub-standards use letter suffixes (a, b, c, d...), not roman numerals
