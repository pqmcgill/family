"""Tests for the structural validator."""

from ingest_standards.models import NodeType, SourceInfo, StandardNode, Subject
from ingest_standards.validator import Severity, validate


def _make_source() -> SourceInfo:
    return SourceInfo(adapter="test", url="https://test", version="2023", retrieved="2026-03-31")


def _make_valid_math_nodes() -> list[StandardNode]:
    """A minimal valid set of math nodes."""
    nodes: list[StandardNode] = []
    for domain in ["NS", "CA", "G", "M", "DA"]:
        nodes.append(
            StandardNode(
                id=f"K.{domain}",
                subject=Subject.MATH,
                grade="K",
                domain=domain,
                type=NodeType.DOMAIN,
                description=f"{domain} Domain",
                source=_make_source(),
            )
        )
        for i in range(1, 4):
            nodes.append(
                StandardNode(
                    id=f"K.{domain}.{i}",
                    subject=Subject.MATH,
                    grade="K",
                    domain=domain,
                    type=NodeType.STANDARD,
                    description=f"Standard {domain}.{i}",
                    essential=i == 1,
                    parent_id=f"K.{domain}",
                    source=_make_source(),
                )
            )
    return nodes


def test_valid_nodes_pass() -> None:
    nodes = _make_valid_math_nodes()
    report = validate(nodes)
    assert report.passed
    assert not report.has_errors


def test_duplicate_ids_fail() -> None:
    nodes = _make_valid_math_nodes()
    # Add a duplicate
    nodes.append(
        StandardNode(
            id="K.NS.1",
            subject=Subject.MATH,
            grade="K",
            domain="NS",
            type=NodeType.STANDARD,
            description="Duplicate!",
            parent_id="K.NS",
            source=_make_source(),
        )
    )
    report = validate(nodes)
    assert report.has_errors
    failed = [c for c in report.checks if c.name == "no_duplicates"]
    assert len(failed) == 1
    assert not failed[0].passed


def test_malformed_code_fails() -> None:
    nodes = [
        StandardNode(
            id="K.NS",
            subject=Subject.MATH,
            grade="K",
            domain="NS",
            type=NodeType.DOMAIN,
            description="Number Sense",
            source=_make_source(),
        ),
        StandardNode(
            id="KBAD1",  # malformed
            subject=Subject.MATH,
            grade="K",
            domain="NS",
            type=NodeType.STANDARD,
            description="Bad code",
            parent_id="K.NS",
            source=_make_source(),
        ),
    ]
    report = validate(nodes)
    code_check = next(c for c in report.checks if c.name == "code_format")
    assert not code_check.passed


def test_missing_parent_fails() -> None:
    nodes = [
        StandardNode(
            id="K.NS.1",
            subject=Subject.MATH,
            grade="K",
            domain="NS",
            type=NodeType.STANDARD,
            description="Orphan standard",
            parent_id="K.NS",  # K.NS domain doesn't exist
            source=_make_source(),
        ),
    ]
    report = validate(nodes)
    hier_check = next(c for c in report.checks if c.name == "hierarchy")
    assert not hier_check.passed


def test_missing_domain_detected() -> None:
    """Math should have all 5 domains. Remove one and check."""
    nodes = _make_valid_math_nodes()
    # Remove all DA nodes
    nodes = [n for n in nodes if n.domain != "DA"]
    report = validate(nodes)
    domain_check = next(c for c in report.checks if c.name == "domain_coverage")
    assert not domain_check.passed
    assert "DA" in domain_check.details[0]


def test_no_essential_is_warning() -> None:
    """Build a complete valid set but with no essential flags."""
    nodes = _make_valid_math_nodes()
    for node in nodes:
        node.essential = False

    report = validate(nodes)
    ess_check = next(c for c in report.checks if c.name == "essential_present")
    assert not ess_check.passed
    assert ess_check.severity == Severity.WARNING
    # Warning, not error — should still pass
    assert not report.has_errors


def test_report_summary_format() -> None:
    nodes = _make_valid_math_nodes()
    report = validate(nodes)
    summary = report.summary()
    assert "PASS" in summary
    assert "0 errors" in summary
