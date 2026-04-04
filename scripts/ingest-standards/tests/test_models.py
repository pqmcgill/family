"""Tests for the canonical data model."""

from ingest_standards.models import (
    NodeType,
    SourceInfo,
    StandardNode,
    Subject,
)


def test_standard_node_creation() -> None:
    node = StandardNode(
        id="K.NS.1",
        subject=Subject.MATH,
        grade="K",
        domain="NS",
        type=NodeType.STANDARD,
        description="Count to at least 100 by ones and tens.",
        essential=True,
        source=SourceInfo(
            adapter="opensalt",
            url="https://opensalt.net/...",
            version="2023",
            retrieved="2026-03-31",
        ),
    )
    assert node.id == "K.NS.1"
    assert node.subject == Subject.MATH
    assert node.essential is True
    assert node.children == []
    assert node.parent_id is None
    assert node.science is None


def test_domain_node() -> None:
    node = StandardNode(
        id="K.NS",
        subject=Subject.MATH,
        grade="K",
        domain="NS",
        type=NodeType.DOMAIN,
        description="Number Sense",
        learning_outcome="Students build understanding of the number system.",
        children=["K.NS.1", "K.NS.2"],
        source=SourceInfo(
            adapter="opensalt",
            url="https://opensalt.net/...",
            version="2023",
            retrieved="2026-03-31",
        ),
    )
    assert node.type == NodeType.DOMAIN
    assert len(node.children) == 2
    assert node.learning_outcome is not None
