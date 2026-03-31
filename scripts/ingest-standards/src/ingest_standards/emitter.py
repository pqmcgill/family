"""Emit validated StandardNodes as YAML files.

Transforms a flat list of StandardNodes into the per-grade YAML file
format defined in DESIGN-EDU-STANDARDS.md. Also generates the manifest
and process standards files.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml

from ingest_standards.models import NodeType, StandardNode, Subject

# Friendly names for subjects in file output
SUBJECT_FILE_PREFIX: dict[Subject, str] = {
    Subject.MATH: "math",
    Subject.ELA: "ela",
    Subject.SCIENCE: "science",
    Subject.SOCIAL_STUDIES: "social-studies",
}


def _standard_to_dict(node: StandardNode) -> dict:
    """Convert a standard node to its YAML representation."""
    d: dict = {"description": node.description, "essential": node.essential}

    if node.sub_domain:
        d["sub_domain"] = node.sub_domain

    if node.science:
        sci = node.science
        if sci.clarification:
            d["clarification"] = sci.clarification
        if sci.practice:
            d["practice"] = sci.practice
        if sci.core_idea:
            d["core_idea"] = sci.core_idea
        if sci.crosscutting:
            d["crosscutting"] = sci.crosscutting
        if sci.boundary:
            d["boundary"] = sci.boundary

    return d


def _domain_to_dict(
    domain_node: StandardNode,
    standards: list[StandardNode],
) -> dict:
    """Convert a domain node and its children to YAML representation."""
    d: dict = {"name": domain_node.description}

    if domain_node.learning_outcome:
        d["learning_outcome"] = domain_node.learning_outcome

    d["standards"] = {}
    for std in sorted(standards, key=lambda s: s.source.retrieved):
        d["standards"][std.id] = _standard_to_dict(std)

    return d


def _build_source_block(nodes: list[StandardNode]) -> dict:
    """Build the source metadata block from node provenance."""
    # Use the first node's source info as representative
    src = nodes[0].source
    block: dict = {
        "primary": src.adapter,
        "primary_url": src.url,
        "last_verified": src.retrieved,
    }
    return block


def emit_grade_file(
    subject: Subject,
    grade: str,
    domain_nodes: list[StandardNode],
    standard_nodes: list[StandardNode],
    output_dir: Path,
) -> Path:
    """Write a single grade-level YAML file.

    Returns the path to the written file.
    """
    prefix = SUBJECT_FILE_PREFIX[subject]
    grade_label = "k" if grade == "K" else grade
    filename = f"{prefix}-{grade_label}.yaml"
    filepath = output_dir / filename

    # Group standards by domain
    standards_by_domain: dict[str, list[StandardNode]] = defaultdict(list)
    for std in standard_nodes:
        standards_by_domain[std.domain].append(std)

    # Sort standards within each domain by ID
    for domain_stds in standards_by_domain.values():
        domain_stds.sort(key=lambda s: s.id)

    # Build domain order from domain_nodes
    all_nodes = domain_nodes + standard_nodes
    standard_count = len(standard_nodes)

    doc: dict = {
        "subject": subject.value,
        "grade": grade,
        "version": all_nodes[0].source.version if all_nodes else "unknown",
        "source": _build_source_block(all_nodes) if all_nodes else {},
        "standard_count": standard_count,
        "domains": {},
    }

    for domain_node in sorted(domain_nodes, key=lambda d: d.id):
        domain_key = domain_node.domain
        domain_standards = standards_by_domain.get(domain_key, [])
        doc["domains"][domain_key] = _domain_to_dict(domain_node, domain_standards)

    filepath.write_text(
        yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return filepath


def emit_process_standards(
    nodes: list[StandardNode],
    output_dir: Path,
) -> Path:
    """Write the cross-grade process standards file."""
    filepath = output_dir / "process-standards.yaml"

    # Group by subject
    by_subject: dict[str, list[StandardNode]] = defaultdict(list)
    for node in nodes:
        by_subject[node.subject.value].append(node)

    doc: dict = {}
    for subject_val, subject_nodes in sorted(by_subject.items()):
        subject_nodes.sort(key=lambda n: n.id)
        doc[subject_val] = {}
        for node in subject_nodes:
            entry: dict = {"description": node.description}
            if node.learning_outcome:
                entry["detail"] = node.learning_outcome
            doc[subject_val][node.id] = entry

    filepath.write_text(
        yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return filepath


def emit_manifest(
    all_nodes: list[StandardNode],
    output_dir: Path,
    validation_results: dict | None = None,
) -> Path:
    """Write the manifest.yaml with provenance and counts."""
    filepath = output_dir / "manifest.yaml"

    # Count standards per subject per grade
    standard_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for node in all_nodes:
        if node.type == NodeType.STANDARD:
            subject_key = SUBJECT_FILE_PREFIX.get(node.subject, node.subject.value)
            standard_counts[subject_key][node.grade] += 1

    # Collect source info
    adapters_used: set[str] = set()
    versions: set[str] = set()
    retrieval_dates: set[str] = set()
    for node in all_nodes:
        adapters_used.add(node.source.adapter)
        versions.add(node.source.version)
        retrieval_dates.add(node.source.retrieved)

    doc: dict = {
        "schema_version": 1,
        "last_ingestion": max(retrieval_dates) if retrieval_dates else "unknown",
        "sources_used": sorted(adapters_used),
        "versions": sorted(versions),
        "standard_counts": {
            subject: dict(sorted(grades.items()))
            for subject, grades in sorted(standard_counts.items())
        },
    }

    if validation_results:
        doc["validation_results"] = validation_results

    filepath.write_text(
        yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return filepath


def emit_all(
    nodes: list[StandardNode],
    output_dir: Path,
    validation_results: dict | None = None,
) -> list[Path]:
    """Emit all YAML files from a list of StandardNodes.

    Returns list of paths written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # Separate process standards from grade-level content
    process_nodes = [n for n in nodes if n.type == NodeType.PROCESS]
    domain_nodes = [n for n in nodes if n.type == NodeType.DOMAIN]
    standard_nodes = [n for n in nodes if n.type == NodeType.STANDARD]

    # Group by (subject, grade)
    grade_domains: dict[tuple[Subject, str], list[StandardNode]] = defaultdict(list)
    grade_standards: dict[tuple[Subject, str], list[StandardNode]] = defaultdict(list)

    for node in domain_nodes:
        grade_domains[(node.subject, node.grade)].append(node)
    for node in standard_nodes:
        grade_standards[(node.subject, node.grade)].append(node)

    # Emit per-grade files
    all_keys = set(grade_domains.keys()) | set(grade_standards.keys())
    for subject, grade in sorted(all_keys):
        path = emit_grade_file(
            subject=subject,
            grade=grade,
            domain_nodes=grade_domains.get((subject, grade), []),
            standard_nodes=grade_standards.get((subject, grade), []),
            output_dir=output_dir,
        )
        written.append(path)

    # Emit process standards
    if process_nodes:
        written.append(emit_process_standards(process_nodes, output_dir))

    # Emit manifest
    written.append(emit_manifest(nodes, output_dir, validation_results))

    return written
