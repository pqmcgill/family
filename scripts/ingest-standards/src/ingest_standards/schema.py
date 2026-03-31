"""YAML schema validation for standards files.

Validates that YAML files produced by PDF extraction (or any source)
conform to the expected structure before downstream consumption.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Valid subjects and their domain codes
VALID_SUBJECTS: dict[str, set[str]] = {
    "math": {"NS", "CA", "G", "M", "DA"},
    "ela": {"RF", "RC", "W", "CC"},
    "science": {"PS1", "PS2", "PS3", "PS4", "LS1", "LS2", "LS3", "LS4", "ESS1", "ESS2", "ESS3", "ETS1"},
    "social_studies": {"H", "C", "G", "E"},
}

VALID_GRADES = {"K", "1", "2", "3", "4", "5"}

# Standard code patterns per subject
CODE_PATTERNS: dict[str, re.Pattern[str]] = {
    "math": re.compile(r"^[K1-5]\.[A-Z]+\.\d+$"),
    "ela": re.compile(r"^[K1-5]\.[A-Z]+\.\d+[a-z]?$"),
    "science": re.compile(r"^[K1-5]-[A-Z]+\d?-\d+$|^K-2-ETS1-\d+$|^3-5-ETS1-\d+$"),
    "social_studies": re.compile(r"^[K1-5]\.[A-Z]+\.\d+$"),
}

REQUIRED_TOP_LEVEL = {"subject", "grade", "version", "source", "standard_count", "domains"}
REQUIRED_SOURCE = {"primary", "primary_url", "last_verified"}
REQUIRED_DOMAIN = {"name", "standards"}
REQUIRED_STANDARD = {"description"}

# Science standards must have these
REQUIRED_SCIENCE_STANDARD = {"description", "practice", "core_idea", "crosscutting"}
VALID_SEPS = {f"SEP.{i}" for i in range(1, 9)}
VALID_CCS = {f"CC.{i}" for i in range(1, 8)}


@dataclass
class SchemaError:
    path: str  # e.g., "domains.NS.standards.K.NS.1.description"
    message: str
    severity: str = "error"  # "error" or "warning"


@dataclass
class SchemaReport:
    file: str
    errors: list[SchemaError] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(e.severity == "error" for e in self.errors)

    def summary(self) -> str:
        lines = [f"Schema validation: {self.file}"]
        if self.passed and not self.errors:
            lines.append("  All checks passed.")
        for err in self.errors:
            marker = "ERROR" if err.severity == "error" else "WARN"
            lines.append(f"  [{marker}] {err.path}: {err.message}")
        error_count = sum(1 for e in self.errors if e.severity == "error")
        warn_count = sum(1 for e in self.errors if e.severity == "warning")
        lines.append(f"  {error_count} errors, {warn_count} warnings")
        return "\n".join(lines)


def _check_required(data: dict, required: set[str], path: str, errors: list[SchemaError]) -> None:
    for key in required:
        if key not in data:
            errors.append(SchemaError(path=f"{path}.{key}", message=f"missing required field '{key}'"))


def _check_standard(
    std_id: str,
    std: dict,
    subject: str,
    path: str,
    errors: list[SchemaError],
) -> None:
    """Validate a single standard entry."""
    if not isinstance(std, dict):
        errors.append(SchemaError(path=path, message="standard must be a mapping"))
        return

    required = REQUIRED_SCIENCE_STANDARD if subject == "science" else REQUIRED_STANDARD
    _check_required(std, required, path, errors)

    # Check description is a string
    desc = std.get("description", "")
    if isinstance(desc, str) and "(E)" in desc:
        errors.append(SchemaError(path=f"{path}.description", message="description contains '(E)' — should be in essential field"))

    # Check essential is bool if present
    if "essential" in std and not isinstance(std["essential"], bool):
        errors.append(SchemaError(path=f"{path}.essential", message=f"essential must be bool, got {type(std['essential']).__name__}"))

    # Science-specific checks
    if subject == "science":
        practice = std.get("practice", "")
        if practice and practice not in VALID_SEPS:
            errors.append(SchemaError(path=f"{path}.practice", message=f"invalid practice code '{practice}', expected SEP.1-SEP.8"))
        cc = std.get("crosscutting", "")
        if cc and cc not in VALID_CCS:
            errors.append(SchemaError(path=f"{path}.crosscutting", message=f"invalid crosscutting code '{cc}', expected CC.1-CC.7"))

    # Check sub_standards if present
    if "sub_standards" in std:
        subs = std["sub_standards"]
        if not isinstance(subs, dict):
            errors.append(SchemaError(path=f"{path}.sub_standards", message="sub_standards must be a mapping"))
        else:
            for sub_id, sub in subs.items():
                if not isinstance(sub, dict):
                    errors.append(SchemaError(path=f"{path}.sub_standards.{sub_id}", message="sub-standard must be a mapping"))
                elif "description" not in sub:
                    errors.append(SchemaError(path=f"{path}.sub_standards.{sub_id}", message="missing description"))


def validate_yaml_file(filepath: Path) -> SchemaReport:
    """Validate a single standards YAML file against the expected schema."""
    report = SchemaReport(file=str(filepath))

    try:
        data = yaml.safe_load(filepath.read_text())
    except Exception as e:
        report.errors.append(SchemaError(path="", message=f"YAML parse error: {e}"))
        return report

    if not isinstance(data, dict):
        report.errors.append(SchemaError(path="", message="top-level must be a mapping"))
        return report

    # Top-level required fields
    _check_required(data, REQUIRED_TOP_LEVEL, "", report.errors)

    subject = data.get("subject", "")
    grade = str(data.get("grade", ""))

    # Validate subject
    if subject not in VALID_SUBJECTS:
        report.errors.append(SchemaError(path="subject", message=f"invalid subject '{subject}'"))
        return report

    # Validate grade
    if grade not in VALID_GRADES:
        report.errors.append(SchemaError(path="grade", message=f"invalid grade '{grade}'"))

    # Validate source
    source = data.get("source", {})
    if isinstance(source, dict):
        _check_required(source, REQUIRED_SOURCE, "source", report.errors)

    # Validate domains
    domains = data.get("domains", {})
    if not isinstance(domains, dict):
        report.errors.append(SchemaError(path="domains", message="domains must be a mapping"))
        return report

    # Check expected domains are present (warning, not error — some grades may not have all)
    expected_domains = VALID_SUBJECTS[subject]
    present_domains = set(domains.keys())
    # For science, not all domain groups appear at every grade, so skip this check
    if subject not in ("science",):
        missing = expected_domains - present_domains
        if missing:
            report.errors.append(SchemaError(
                path="domains", message=f"missing expected domains: {missing}", severity="warning"
            ))

    unexpected = present_domains - expected_domains
    if unexpected:
        report.errors.append(SchemaError(
            path="domains", message=f"unexpected domains: {unexpected}"
        ))

    # Validate each domain
    code_pattern = CODE_PATTERNS.get(subject)
    actual_leaf_count = 0

    for domain_key, domain in domains.items():
        dpath = f"domains.{domain_key}"
        if not isinstance(domain, dict):
            report.errors.append(SchemaError(path=dpath, message="domain must be a mapping"))
            continue

        _check_required(domain, REQUIRED_DOMAIN, dpath, report.errors)

        standards = domain.get("standards", {})
        if not isinstance(standards, dict):
            report.errors.append(SchemaError(path=f"{dpath}.standards", message="standards must be a mapping"))
            continue

        for std_id, std in standards.items():
            spath = f"{dpath}.standards.{std_id}"

            # Validate code format
            if code_pattern and not code_pattern.match(std_id):
                report.errors.append(SchemaError(path=spath, message=f"code '{std_id}' doesn't match expected pattern"))

            _check_standard(std_id, std, subject, spath, report.errors)

            # Count leaf standards
            if isinstance(std, dict) and "sub_standards" in std:
                actual_leaf_count += len(std["sub_standards"])
            else:
                actual_leaf_count += 1

    # Validate standard_count matches
    declared_count = data.get("standard_count", 0)
    if actual_leaf_count != declared_count:
        report.errors.append(SchemaError(
            path="standard_count",
            message=f"declared {declared_count} but found {actual_leaf_count} leaf standards",
        ))

    return report


def validate_all(standards_dir: Path) -> list[SchemaReport]:
    """Validate all standards YAML files in a directory."""
    reports: list[SchemaReport] = []
    for filepath in sorted(standards_dir.glob("*.yaml")):
        if filepath.name in ("manifest.yaml", "process-standards.yaml"):
            continue
        reports.append(validate_yaml_file(filepath))
    return reports
