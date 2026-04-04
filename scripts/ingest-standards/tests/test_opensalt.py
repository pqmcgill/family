"""Tests for the OpenSALT adapter."""

from ingest_standards.adapters.opensalt import OpenSaltAdapter, _parse_essential
from ingest_standards.models import NodeType, Subject


FIXTURE_PACKAGE = {
    "CFDocument": {
        "identifier": "76673c2e-5cb6-11ee-a3bc-0242c0a84002",
        "title": "Indiana Academic Standards for Mathematics (2023)",
    },
    "CFItems": [
        # Process standard
        {
            "identifier": "ps1-uuid",
            "fullStatement": "Make sense of problems and persevere in solving them.",
            "CFItemType": "Process Standard",
            "humanCodingScheme": "PS.1",
            "educationLevel": ["KG", "01", "02", "03", "04", "05"],
            "notes": "Mathematically proficient students start by explaining...",
        },
        # Domain
        {
            "identifier": "kns-domain-uuid",
            "fullStatement": "Number Sense",
            "CFItemType": "Domain",
            "humanCodingScheme": "K.NS",
            "educationLevel": ["KG"],
            "notes": "Learning Outcome: Students explore the foundations of numbers through counting strategies.",
        },
        # Standards under K.NS
        {
            "identifier": "kns1-uuid",
            "fullStatement": "Count to at least 100 by ones and tens. Count by one from any given number. (E)",
            "CFItemType": "Standard",
            "humanCodingScheme": "K.NS.1",
            "educationLevel": ["KG"],
        },
        {
            "identifier": "kns2-uuid",
            "fullStatement": "Write whole numbers from 0 to 20.",
            "CFItemType": "Standard",
            "humanCodingScheme": "K.NS.2",
            "educationLevel": ["KG"],
        },
        # Domain for grade 1
        {
            "identifier": "1ca-domain-uuid",
            "fullStatement": "Computation and Algebraic Thinking",
            "CFItemType": "Domain",
            "humanCodingScheme": "1.CA",
            "educationLevel": ["01"],
            "notes": "Learning Outcome: Students demonstrate fluency with addition and subtraction.",
        },
        # Standard under 1.CA
        {
            "identifier": "1ca1-uuid",
            "fullStatement": "Demonstrate fluency with addition facts within 20. (E)",
            "CFItemType": "Standard",
            "humanCodingScheme": "1.CA.1",
            "educationLevel": ["01"],
        },
        # Grade level item (should be skipped)
        {
            "identifier": "grade-k-uuid",
            "fullStatement": "Kindergarten",
            "CFItemType": "Grade Level",
            "humanCodingScheme": "",
            "educationLevel": ["KG"],
        },
        # Grade 7 standard (should be filtered out — not in K-5)
        {
            "identifier": "7ns1-uuid",
            "fullStatement": "Compute unit rates associated with ratios of fractions.",
            "CFItemType": "Standard",
            "humanCodingScheme": "7.NS.1",
            "educationLevel": ["07"],
        },
        # Top-level container (should be skipped — no humanCodingScheme)
        {
            "identifier": "container-uuid",
            "fullStatement": "Standards for Math Content",
            "CFItemType": None,
            "educationLevel": ["KG", "01"],
            "notes": "Standards identified as essential...",
        },
    ],
}


def test_parse_essential_with_marker() -> None:
    text, essential = _parse_essential("Count to at least 100. (E)")
    assert text == "Count to at least 100."
    assert essential is True


def test_parse_essential_without_marker() -> None:
    text, essential = _parse_essential("Write whole numbers from 0 to 20.")
    assert text == "Write whole numbers from 0 to 20."
    assert essential is False


def test_adapter_yields_process_standards() -> None:
    adapter = OpenSaltAdapter("math", "2023", package_data=FIXTURE_PACKAGE)
    nodes = list(adapter.fetch())

    process = [n for n in nodes if n.type == NodeType.PROCESS]
    assert len(process) == 1
    assert process[0].id == "PS.1"
    assert process[0].grade == "all"
    assert process[0].domain == "PS"
    assert "Make sense of problems" in process[0].description


def test_adapter_yields_domains() -> None:
    adapter = OpenSaltAdapter("math", "2023", package_data=FIXTURE_PACKAGE)
    nodes = list(adapter.fetch())

    domains = [n for n in nodes if n.type == NodeType.DOMAIN]
    assert len(domains) == 2
    domain_ids = {d.id for d in domains}
    assert domain_ids == {"K.NS", "1.CA"}

    kns = next(d for d in domains if d.id == "K.NS")
    assert kns.learning_outcome is not None
    assert "foundations of numbers" in kns.learning_outcome


def test_adapter_yields_standards() -> None:
    adapter = OpenSaltAdapter("math", "2023", package_data=FIXTURE_PACKAGE)
    nodes = list(adapter.fetch())

    standards = [n for n in nodes if n.type == NodeType.STANDARD]
    assert len(standards) == 3  # K.NS.1, K.NS.2, 1.CA.1

    kns1 = next(s for s in standards if s.id == "K.NS.1")
    assert kns1.essential is True
    assert kns1.parent_id == "K.NS"
    assert kns1.grade == "K"
    assert kns1.domain == "NS"
    assert kns1.subject == Subject.MATH
    assert "(E)" not in kns1.description  # stripped

    kns2 = next(s for s in standards if s.id == "K.NS.2")
    assert kns2.essential is False


def test_adapter_filters_out_high_grades() -> None:
    adapter = OpenSaltAdapter("math", "2023", package_data=FIXTURE_PACKAGE)
    nodes = list(adapter.fetch())

    all_ids = {n.id for n in nodes}
    assert "7.NS.1" not in all_ids


def test_adapter_skips_items_without_code() -> None:
    adapter = OpenSaltAdapter("math", "2023", package_data=FIXTURE_PACKAGE)
    nodes = list(adapter.fetch())

    # Grade level item and container should not appear
    all_ids = {n.id for n in nodes}
    assert "" not in all_ids
    assert "Kindergarten" not in all_ids


def test_adapter_source_info() -> None:
    adapter = OpenSaltAdapter("math", "2023", package_data=FIXTURE_PACKAGE)
    nodes = list(adapter.fetch())

    for node in nodes:
        assert node.source.adapter == "opensalt"
        assert node.source.version == "2023"
        assert "opensalt.net" in node.source.url
