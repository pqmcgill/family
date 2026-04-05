"""Chunk family data files into semantic units for indexing."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def chunk_file(file_path: Path) -> list[dict]:
    """Route a file to the appropriate chunker based on its path and type."""
    rel = str(file_path)

    if "checkins/" in rel and file_path.suffix == ".md":
        return _chunk_checkin(file_path)
    elif file_path.name == "plan.md" and "weeks/" in rel:
        return _chunk_plan(file_path)
    elif file_path.name == "current.yaml":
        return _chunk_current_yaml(file_path)
    elif file_path.name == "coverage.yaml" and "edu" in rel:
        return _chunk_coverage(file_path)
    elif "activity-log/" in rel and file_path.suffix == ".md":
        return _chunk_activity_log(file_path)
    elif "standards/" in rel and file_path.suffix in (".yaml", ".yml"):
        return _chunk_standards_yaml(file_path)
    else:
        # Generic: treat entire file as one chunk
        return _chunk_generic(file_path)


def _extract_date_from_path(file_path: Path) -> str:
    """Try to extract a date from the file path or content.

    Looks for week patterns (YYYY-WXX) and day names in checkin filenames.
    """
    parts = str(file_path).split("/")

    # Find week folder like 2026-W14
    week = ""
    for part in parts:
        if re.match(r"\d{4}-W\d{2}", part):
            week = part
            break

    # For checkins, the filename is the day
    if file_path.stem in ("mon", "tue", "wed", "thu", "fri", "sat", "sun"):
        return f"{week}/{file_path.stem}" if week else file_path.stem

    # For activity logs, filename might be a date
    if re.match(r"\d{4}-\d{2}-\d{2}", file_path.stem):
        return file_path.stem

    return week


def _chunk_checkin(file_path: Path) -> list[dict]:
    """Split a checkin log into one chunk per domain section."""
    content = file_path.read_text()
    date = _extract_date_from_path(file_path)
    source = str(file_path)

    chunks = []
    # Split on ## headings (domain sections)
    sections = re.split(r"^## ", content, flags=re.MULTILINE)

    for section in sections:
        if not section.strip():
            continue

        lines = section.strip().split("\n")
        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()

        if not body:
            continue

        domain = _normalize_domain(heading)
        chunk_id = f"{source}::{domain}"

        chunks.append({
            "id": chunk_id,
            "text": f"{heading}\n{body}",
            "source_file": source,
            "date": date,
            "type": "checkin",
            "domain": domain,
        })

    return chunks


def _chunk_plan(file_path: Path) -> list[dict]:
    """Split a weekly plan into caregiver checklist and partner insights."""
    content = file_path.read_text()
    date = _extract_date_from_path(file_path)
    source = str(file_path)

    chunks = []

    # Split on top-level headings (# or ##)
    sections = re.split(r"^# ", content, flags=re.MULTILINE)

    for section in sections:
        if not section.strip():
            continue

        lines = section.strip().split("\n")
        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()

        if not body:
            continue

        # Determine type based on heading content
        heading_lower = heading.lower()
        if "checklist" in heading_lower or "caregiver" in heading_lower:
            chunk_type = "plan_checklist"
        elif "insight" in heading_lower or "partner" in heading_lower:
            chunk_type = "plan_insights"
        elif "calendar" in heading_lower:
            chunk_type = "plan_calendar"
        else:
            chunk_type = "plan"

        chunk_id = f"{source}::{chunk_type}"
        chunks.append({
            "id": chunk_id,
            "text": f"{heading}\n{body}",
            "source_file": source,
            "date": date,
            "type": chunk_type,
            "domain": "",
        })

    return chunks


def _chunk_current_yaml(file_path: Path) -> list[dict]:
    """Split current.yaml into one chunk per top-level key."""
    content = file_path.read_text()
    source = str(file_path)

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        return _chunk_generic(file_path)

    if not isinstance(data, dict):
        return _chunk_generic(file_path)

    chunks = []
    for key, value in data.items():
        text = yaml.dump({key: value}, default_flow_style=False, allow_unicode=True)
        domain = _normalize_domain(key)
        chunk_id = f"{source}::{key}"

        chunks.append({
            "id": chunk_id,
            "text": text,
            "source_file": source,
            "date": "",
            "type": "state",
            "domain": domain,
        })

    return chunks


def _chunk_coverage(file_path: Path) -> list[dict]:
    """Split coverage.yaml into one chunk per standard."""
    content = file_path.read_text()
    source = str(file_path)

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        return _chunk_generic(file_path)

    if not isinstance(data, dict):
        return _chunk_generic(file_path)

    standards = data.get("standards", {})
    chunks = []

    for std_id, info in standards.items():
        text = f"Standard {std_id}: {yaml.dump(info, default_flow_style=False)}"
        chunk_id = f"{source}::{std_id}"

        chunks.append({
            "id": chunk_id,
            "text": text,
            "source_file": source,
            "date": info.get("last_touched", ""),
            "type": "coverage",
            "domain": _subject_from_standard_id(std_id),
        })

    return chunks


def _chunk_activity_log(file_path: Path) -> list[dict]:
    """Chunk an education activity log — one chunk per activity entry."""
    content = file_path.read_text()
    date = _extract_date_from_path(file_path)
    source = str(file_path)

    # Split on ## headings (each activity)
    sections = re.split(r"^## ", content, flags=re.MULTILINE)

    chunks = []
    for i, section in enumerate(sections):
        if not section.strip():
            continue

        lines = section.strip().split("\n")
        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        text = f"{heading}\n{body}" if body else heading

        chunk_id = f"{source}::activity_{i}"
        chunks.append({
            "id": chunk_id,
            "text": text,
            "source_file": source,
            "date": date,
            "type": "activity",
            "domain": "education",
        })

    return chunks


def _chunk_standards_yaml(file_path: Path) -> list[dict]:
    """Split a standards YAML file into one chunk per standard."""
    content = file_path.read_text()
    source = str(file_path)

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        return _chunk_generic(file_path)

    if not isinstance(data, dict) or "domains" not in data:
        return _chunk_generic(file_path)

    subject = data.get("subject", "")
    grade = data.get("grade", "")
    domains = data.get("domains", {})
    chunks = []

    for domain_id, domain_info in domains.items():
        domain_name = domain_info.get("name", domain_id)
        standards = domain_info.get("standards", {})

        for std_id, std_info in standards.items():
            description = std_info.get("description", "")
            essential = std_info.get("essential", False)

            # Build a rich text representation for embedding
            parts = [f"{std_id}: {description}"]
            if essential:
                parts.append("(Essential)")
            parts.append(f"Subject: {subject}, Grade: {grade}, Domain: {domain_name}")

            # Include sub-standards if present
            sub_standards = std_info.get("sub_standards", {})
            for sub_id, sub_info in sub_standards.items():
                sub_desc = sub_info.get("description", "")
                parts.append(f"  {sub_id}: {sub_desc}")

            # Include science-specific fields
            for field in ("clarification", "practice", "core_idea", "crosscutting"):
                if field in std_info:
                    parts.append(f"{field}: {std_info[field]}")

            chunk_id = f"{source}::{std_id}"
            chunks.append({
                "id": chunk_id,
                "text": "\n".join(parts),
                "source_file": source,
                "date": "",
                "type": "standard",
                "domain": subject,
            })

    return chunks


def _chunk_generic(file_path: Path) -> list[dict]:
    """Treat the whole file as a single chunk."""
    content = file_path.read_text()
    if not content.strip():
        return []

    return [{
        "id": str(file_path),
        "text": content,
        "source_file": str(file_path),
        "date": _extract_date_from_path(file_path),
        "type": "generic",
        "domain": "",
    }]


def _normalize_domain(name: str) -> str:
    """Normalize a domain name for consistent metadata."""
    return name.lower().replace(" ", "_").replace("/", "_")


def _subject_from_standard_id(std_id: str) -> str:
    """Infer subject from a standard ID like K.NS.1 or 1-PS4-1."""
    if "-" in std_id and any(x in std_id.upper() for x in ("PS", "LS", "ESS", "ETS")):
        return "science"
    parts = std_id.split(".")
    if len(parts) >= 2:
        domain = parts[1].upper()
        if domain in ("NS", "CA", "G", "M", "DA"):
            return "math"
        if domain in ("RF", "RC", "W", "CC"):
            return "ela"
        if domain in ("H", "C", "E"):
            return "social_studies"
    return ""
