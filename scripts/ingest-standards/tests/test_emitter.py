"""Tests for the YAML emitter."""

from pathlib import Path

import yaml

from ingest_standards.emitter import emit_all, emit_grade_file
from ingest_standards.models import NodeType, SourceInfo, StandardNode, Subject


def _make_source() -> SourceInfo:
    return SourceInfo(adapter="test", url="https://test", version="2023", retrieved="2026-03-31")


def _make_math_k_nodes() -> list[StandardNode]:
    """Create a small set of Math K nodes for testing."""
    return [
        StandardNode(
            id="K.NS",
            subject=Subject.MATH,
            grade="K",
            domain="NS",
            type=NodeType.DOMAIN,
            description="Number Sense",
            learning_outcome="Students explore the foundations of numbers.",
            children=["K.NS.1", "K.NS.2"],
            source=_make_source(),
        ),
        StandardNode(
            id="K.NS.1",
            subject=Subject.MATH,
            grade="K",
            domain="NS",
            type=NodeType.STANDARD,
            description="Count to at least 100 by ones and tens.",
            essential=True,
            parent_id="K.NS",
            source=_make_source(),
        ),
        StandardNode(
            id="K.NS.2",
            subject=Subject.MATH,
            grade="K",
            domain="NS",
            type=NodeType.STANDARD,
            description="Write whole numbers from 0 to 20.",
            essential=False,
            parent_id="K.NS",
            source=_make_source(),
        ),
        StandardNode(
            id="K.G",
            subject=Subject.MATH,
            grade="K",
            domain="G",
            type=NodeType.DOMAIN,
            description="Geometry",
            learning_outcome="Students identify basic shapes.",
            source=_make_source(),
        ),
        StandardNode(
            id="K.G.1",
            subject=Subject.MATH,
            grade="K",
            domain="G",
            type=NodeType.STANDARD,
            description="Describe objects using names of shapes.",
            essential=True,
            parent_id="K.G",
            source=_make_source(),
        ),
    ]


def test_emit_grade_file(tmp_path: Path) -> None:
    nodes = _make_math_k_nodes()
    domains = [n for n in nodes if n.type == NodeType.DOMAIN]
    standards = [n for n in nodes if n.type == NodeType.STANDARD]

    path = emit_grade_file(Subject.MATH, "K", domains, standards, tmp_path)

    assert path.name == "math-k.yaml"
    assert path.exists()

    data = yaml.safe_load(path.read_text())

    assert data["subject"] == "math"
    assert data["grade"] == "K"
    assert data["version"] == "2023"
    assert data["standard_count"] == 3
    assert "NS" in data["domains"]
    assert "G" in data["domains"]

    ns = data["domains"]["NS"]
    assert ns["name"] == "Number Sense"
    assert "foundations" in ns["learning_outcome"]
    assert "K.NS.1" in ns["standards"]
    assert ns["standards"]["K.NS.1"]["essential"] is True
    assert ns["standards"]["K.NS.2"]["essential"] is False


def test_emit_all_produces_expected_files(tmp_path: Path) -> None:
    nodes = _make_math_k_nodes()
    # Add a process standard
    nodes.append(
        StandardNode(
            id="PS.1",
            subject=Subject.MATH,
            grade="all",
            domain="PS",
            type=NodeType.PROCESS,
            description="Make sense of problems and persevere in solving them.",
            learning_outcome="Detail about PS.1...",
            source=_make_source(),
        )
    )

    paths = emit_all(nodes, tmp_path)
    filenames = {p.name for p in paths}

    assert "math-k.yaml" in filenames
    assert "process-standards.yaml" in filenames
    assert "manifest.yaml" in filenames


def test_manifest_contains_counts(tmp_path: Path) -> None:
    nodes = _make_math_k_nodes()
    emit_all(nodes, tmp_path)

    manifest = yaml.safe_load((tmp_path / "manifest.yaml").read_text())
    assert manifest["schema_version"] == 1
    assert "math" in manifest["standard_counts"]
    assert manifest["standard_counts"]["math"]["K"] == 3


def test_process_standards_file(tmp_path: Path) -> None:
    nodes = [
        StandardNode(
            id="PS.1",
            subject=Subject.MATH,
            grade="all",
            domain="PS",
            type=NodeType.PROCESS,
            description="Make sense of problems.",
            learning_outcome="Detailed description...",
            source=_make_source(),
        ),
        StandardNode(
            id="PS.2",
            subject=Subject.MATH,
            grade="all",
            domain="PS",
            type=NodeType.PROCESS,
            description="Reason abstractly.",
            source=_make_source(),
        ),
    ]

    emit_all(nodes, tmp_path)
    data = yaml.safe_load((tmp_path / "process-standards.yaml").read_text())

    assert "math" in data
    assert "PS.1" in data["math"]
    assert data["math"]["PS.1"]["description"] == "Make sense of problems."
    assert data["math"]["PS.1"]["detail"] == "Detailed description..."
    assert "detail" not in data["math"]["PS.2"]  # no learning_outcome
