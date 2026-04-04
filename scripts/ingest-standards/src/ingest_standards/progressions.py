"""Generate vertical articulation / domain progression views.

Produces a markdown file showing how standards build across grades
within each domain. This helps the agent see the full K-5 chain for
any domain at a glance, catching related standards at lower and higher
grade levels when mapping activities.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml

GRADE_ORDER = ["K", "1", "2", "3", "4", "5"]

# Friendly domain names
DOMAIN_NAMES: dict[str, dict[str, str]] = {
    "math": {
        "NS": "Number Sense",
        "CA": "Computation & Algebraic Thinking",
        "G": "Geometry",
        "M": "Measurement",
        "DA": "Data Analysis",
    },
    "ela": {
        "RF": "Reading Foundations",
        "RC": "Reading Comprehension",
        "W": "Writing",
        "CC": "Communication & Collaboration",
    },
    "science": {
        "PS1": "Matter and Its Interactions",
        "PS2": "Motion and Stability: Forces",
        "PS3": "Energy",
        "PS4": "Waves and Information Transfer",
        "LS1": "From Molecules to Organisms",
        "LS2": "Ecosystems: Interactions",
        "LS3": "Heredity",
        "LS4": "Biological Evolution",
        "ESS1": "Earth's Place in the Universe",
        "ESS2": "Earth's Systems",
        "ESS3": "Earth and Human Activity",
        "ETS1": "Engineering Design",
    },
    "social_studies": {
        "H": "History",
        "C": "Civics & Government",
        "G": "Geography",
        "E": "Economics",
    },
}

SUBJECT_NAMES = {
    "math": "Math",
    "ela": "ELA",
    "science": "Science",
    "social_studies": "Social Studies",
}

SUBJECT_ORDER = ["math", "ela", "science", "social_studies"]


def _truncate(text: str, max_len: int = 120) -> str:
    """Truncate description for the progression view."""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def generate_progressions(standards_dir: Path) -> str:
    """Generate the progressions markdown from standards YAML files."""
    # Collect: {subject: {domain: [(grade, std_id, description, essential)]}}
    data: dict[str, dict[str, list[tuple[str, str, str, bool]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for f in sorted(standards_dir.glob("*.yaml")):
        if f.name in ("manifest.yaml", "process-standards.yaml"):
            continue
        if f.suffix != ".yaml":
            continue

        doc = yaml.safe_load(f.read_text())
        if not isinstance(doc, dict) or "domains" not in doc:
            continue

        subject = doc["subject"]
        grade = str(doc["grade"])

        for domain_code, domain in doc["domains"].items():
            for std_id, std in domain.get("standards", {}).items():
                if not isinstance(std, dict):
                    continue
                desc = std.get("description", "")
                ess = std.get("essential", False)
                data[subject][domain_code].append((grade, std_id, desc, ess))

    # Build markdown
    lines: list[str] = []
    lines.append("# Standards Progressions — Vertical Articulation")
    lines.append("")
    lines.append(
        "How standards build across grades K-5 within each domain. "
        "Use this when mapping activities to catch related standards "
        "at lower and higher grade levels."
    )
    lines.append("")
    lines.append(
        "**When you map an activity to a standard, scan the same domain "
        "in this file to find related standards at other grade levels.**"
    )

    for subject in SUBJECT_ORDER:
        if subject not in data:
            continue
        subject_name = SUBJECT_NAMES.get(subject, subject)
        lines.append("")
        lines.append(f"## {subject_name}")

        domain_names = DOMAIN_NAMES.get(subject, {})
        # Sort domains by their order in the DOMAIN_NAMES dict
        domain_order = list(domain_names.keys())
        domains_sorted = sorted(
            data[subject].keys(),
            key=lambda d: domain_order.index(d) if d in domain_order else 999,
        )

        for domain_code in domains_sorted:
            standards = data[subject][domain_code]
            domain_name = domain_names.get(domain_code, domain_code)
            lines.append("")
            lines.append(f"### {domain_code}: {domain_name}")
            lines.append("")

            # Sort by grade, then by standard ID
            grade_key = {g: i for i, g in enumerate(GRADE_ORDER)}
            standards.sort(key=lambda s: (grade_key.get(s[0], 99), s[1]))

            current_grade = None
            for grade, std_id, desc, essential in standards:
                if grade != current_grade:
                    current_grade = grade
                    grade_label = f"K" if grade == "K" else f"Grade {grade}"
                    lines.append(f"**{grade_label}**")

                ess_marker = " **(E)**" if essential else ""
                lines.append(f"- `{std_id}`: {_truncate(desc)}{ess_marker}")

            lines.append("")

    return "\n".join(lines)


def write_progressions(standards_dir: Path) -> Path:
    """Generate and write the progressions file."""
    content = generate_progressions(standards_dir)
    output = standards_dir / "progressions.md"
    output.write_text(content, encoding="utf-8")
    return output
