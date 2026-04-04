"""Live integration test against OpenSALT API.

Run with: uv run pytest tests/test_opensalt_live.py -v
Skipped by default — requires network access.
"""

import os

import pytest

from ingest_standards.adapters.opensalt import OpenSaltAdapter
from ingest_standards.models import NodeType, Subject

pytestmark = pytest.mark.skipif(
    os.environ.get("LIVE_TESTS") != "1",
    reason="Set LIVE_TESTS=1 to run against live APIs",
)


EXPECTED_MATH_DOMAINS = {"NS", "CA", "G", "M", "DA"}


def test_fetch_math_2023() -> None:
    adapter = OpenSaltAdapter("math", "2023")
    nodes = list(adapter.fetch())

    # Should have a reasonable number of nodes
    assert len(nodes) > 100

    # Check node type distribution
    process = [n for n in nodes if n.type == NodeType.PROCESS]
    domains = [n for n in nodes if n.type == NodeType.DOMAIN]
    standards = [n for n in nodes if n.type == NodeType.STANDARD]

    assert len(process) == 8  # PS.1 through PS.8
    assert len(domains) >= 25  # 5 domains × 6 grades (K-5) = 30, minus any missing
    assert len(standards) >= 100

    # All nodes should be math
    for node in nodes:
        assert node.subject == Subject.MATH

    # K-5 grades only (plus "all" for process standards)
    grades = {n.grade for n in nodes}
    assert grades <= {"all", "K", "1", "2", "3", "4", "5"}

    # All 5 math domains should appear for each grade K-5
    for grade in ["K", "1", "2", "3", "4", "5"]:
        grade_domains = {n.domain for n in domains if n.grade == grade}
        assert grade_domains == EXPECTED_MATH_DOMAINS, (
            f"Grade {grade} missing domains: {EXPECTED_MATH_DOMAINS - grade_domains}"
        )

    # Essential standards should exist
    essential_count = sum(1 for n in standards if n.essential)
    assert essential_count > 0

    # Every standard should have a parent_id pointing to a domain
    domain_ids = {d.id for d in domains}
    for std in standards:
        assert std.parent_id is not None
        assert std.parent_id in domain_ids, (
            f"{std.id} has parent_id={std.parent_id} which is not a known domain"
        )

    # Print summary
    print(f"\nFetched {len(nodes)} total nodes:")
    print(f"  {len(process)} process standards")
    print(f"  {len(domains)} domains")
    print(f"  {len(standards)} standards ({essential_count} essential)")
    for grade in ["K", "1", "2", "3", "4", "5"]:
        count = sum(1 for n in standards if n.grade == grade)
        print(f"  Grade {grade}: {count} standards")
