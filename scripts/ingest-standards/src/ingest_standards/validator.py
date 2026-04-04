"""Cross-source and structural validation for standards data.

Runs checks against a list of StandardNodes and produces a report.
Error-severity failures should block YAML emission.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from ingest_standards.models import NodeType, StandardNode, Subject

# Expected domains per subject
EXPECTED_DOMAINS: dict[Subject, set[str]] = {
    Subject.MATH: {"NS", "CA", "G", "M", "DA"},
    Subject.ELA: {"RF", "RC", "W", "CC"},
    Subject.SCIENCE: {"PS1", "PS2", "PS3", "PS4", "LS1", "LS2", "LS3", "ESS1", "ESS2", "ESS3", "ETS1"},
    Subject.SOCIAL_STUDIES: {"H", "C", "G", "E"},
}

# Regex patterns for standard codes per subject
CODE_PATTERNS: dict[Subject, re.Pattern[str]] = {
    Subject.MATH: re.compile(r"^[K1-8]\.[A-Z]+\.\d+$"),
    Subject.ELA: re.compile(r"^[K1-8]\.[A-Z]+\.\d+[a-z]?$"),
    Subject.SCIENCE: re.compile(r"^\d-[A-Z]+\d?-\d+$"),
    Subject.SOCIAL_STUDIES: re.compile(r"^[K1-8]\.[A-Z]+\.\d+$"),
}


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class CheckResult:
    name: str
    severity: Severity
    passed: bool
    message: str
    details: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(
            not c.passed and c.severity == Severity.ERROR for c in self.checks
        )

    @property
    def passed(self) -> bool:
        return not self.has_errors

    def summary(self) -> str:
        lines: list[str] = []
        for check in self.checks:
            status = "PASS" if check.passed else check.severity.value.upper()
            lines.append(f"[{status:>7}] {check.name}: {check.message}")
            for detail in check.details:
                lines.append(f"          {detail}")
        errors = sum(1 for c in self.checks if not c.passed and c.severity == Severity.ERROR)
        warnings = sum(1 for c in self.checks if not c.passed and c.severity == Severity.WARNING)
        passed = sum(1 for c in self.checks if c.passed)
        lines.append(f"\n{passed} passed, {warnings} warnings, {errors} errors")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Summarize for manifest.yaml."""
        result: dict = {}
        for check in self.checks:
            result[check.name] = "pass" if check.passed else f"fail ({check.severity.value})"
        return result


def _check_code_format(nodes: list[StandardNode]) -> CheckResult:
    """Check that all standard codes match expected format for their subject."""
    bad: list[str] = []
    standards = [n for n in nodes if n.type == NodeType.STANDARD]

    for node in standards:
        pattern = CODE_PATTERNS.get(node.subject)
        if pattern and not pattern.match(node.id):
            bad.append(f"{node.id} (subject={node.subject.value})")

    if bad:
        return CheckResult(
            name="code_format",
            severity=Severity.ERROR,
            passed=False,
            message=f"{len(bad)} standards have malformed codes",
            details=bad[:10],
        )
    return CheckResult(
        name="code_format",
        severity=Severity.ERROR,
        passed=True,
        message=f"All {len(standards)} standard codes match expected format",
    )


def _check_domain_coverage(nodes: list[StandardNode]) -> CheckResult:
    """Check that all expected domains are present for each grade."""
    domains = [n for n in nodes if n.type == NodeType.DOMAIN]
    missing: list[str] = []

    # Group domains by (subject, grade)
    present: dict[tuple[Subject, str], set[str]] = defaultdict(set)
    for node in domains:
        present[(node.subject, node.grade)].add(node.domain)

    for (subject, grade), found in sorted(present.items()):
        expected = EXPECTED_DOMAINS.get(subject)
        if expected is None:
            continue
        # Not all subjects have all domains at every grade (e.g., science)
        # So we only check subjects with fixed domain sets
        if subject in (Subject.MATH, Subject.SOCIAL_STUDIES):
            diff = expected - found
            if diff:
                missing.append(f"Grade {grade} {subject.value}: missing {diff}")

    if missing:
        return CheckResult(
            name="domain_coverage",
            severity=Severity.ERROR,
            passed=False,
            message=f"{len(missing)} grade/subject combinations missing domains",
            details=missing,
        )
    return CheckResult(
        name="domain_coverage",
        severity=Severity.ERROR,
        passed=True,
        message="All expected domains present",
    )


def _check_hierarchy(nodes: list[StandardNode]) -> CheckResult:
    """Check that parent-child references are valid."""
    all_ids = {n.id for n in nodes}
    orphans: list[str] = []

    for node in nodes:
        if node.parent_id and node.parent_id not in all_ids:
            orphans.append(f"{node.id} -> parent {node.parent_id} not found")

    if orphans:
        return CheckResult(
            name="hierarchy",
            severity=Severity.ERROR,
            passed=False,
            message=f"{len(orphans)} standards reference missing parents",
            details=orphans[:10],
        )
    return CheckResult(
        name="hierarchy",
        severity=Severity.ERROR,
        passed=True,
        message="All parent references valid",
    )


def _check_no_duplicates(nodes: list[StandardNode]) -> CheckResult:
    """Check for duplicate standard IDs."""
    seen: dict[str, int] = defaultdict(int)
    for node in nodes:
        seen[node.id] += 1

    dupes = {k: v for k, v in seen.items() if v > 1}
    if dupes:
        details = [f"{k} appears {v} times" for k, v in sorted(dupes.items())]
        return CheckResult(
            name="no_duplicates",
            severity=Severity.ERROR,
            passed=False,
            message=f"{len(dupes)} duplicate IDs",
            details=details[:10],
        )
    return CheckResult(
        name="no_duplicates",
        severity=Severity.ERROR,
        passed=True,
        message=f"All {len(nodes)} node IDs are unique",
    )


def _check_essential_present(nodes: list[StandardNode]) -> CheckResult:
    """Check that at least some standards are marked essential."""
    standards = [n for n in nodes if n.type == NodeType.STANDARD]
    essential = [n for n in standards if n.essential]

    if not essential:
        return CheckResult(
            name="essential_present",
            severity=Severity.WARNING,
            passed=False,
            message="No standards marked essential",
        )
    return CheckResult(
        name="essential_present",
        severity=Severity.WARNING,
        passed=True,
        message=f"{len(essential)}/{len(standards)} standards marked essential",
    )


def _check_standard_counts(nodes: list[StandardNode]) -> CheckResult:
    """Sanity check on standard counts per grade."""
    standards = [n for n in nodes if n.type == NodeType.STANDARD]
    by_grade: dict[str, int] = defaultdict(int)
    for node in standards:
        by_grade[node.grade] += 1

    details = [f"Grade {g}: {c}" for g, c in sorted(by_grade.items())]

    # Flag if any grade has suspiciously few or many standards
    suspicious: list[str] = []
    for grade, count in by_grade.items():
        if count < 5:
            suspicious.append(f"Grade {grade} has only {count} standards")
        if count > 60:
            suspicious.append(f"Grade {grade} has {count} standards (unusually high)")

    if suspicious:
        return CheckResult(
            name="standard_counts",
            severity=Severity.WARNING,
            passed=False,
            message="Suspicious standard counts",
            details=suspicious + details,
        )
    return CheckResult(
        name="standard_counts",
        severity=Severity.INFO,
        passed=True,
        message=f"{len(standards)} standards across {len(by_grade)} grades",
        details=details,
    )


def validate(nodes: list[StandardNode]) -> ValidationReport:
    """Run all structural validation checks against a set of nodes.

    Returns a ValidationReport. Check report.has_errors before emitting.
    """
    report = ValidationReport()
    report.checks.append(_check_no_duplicates(nodes))
    report.checks.append(_check_code_format(nodes))
    report.checks.append(_check_domain_coverage(nodes))
    report.checks.append(_check_hierarchy(nodes))
    report.checks.append(_check_essential_present(nodes))
    report.checks.append(_check_standard_counts(nodes))
    return report
