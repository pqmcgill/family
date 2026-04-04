"""Adapter for the OpenSALT CASE API.

Fetches Indiana Academic Standards from the public CASE v1p0 endpoint
at opensalt.net. Currently supports Math 2023.

API docs: https://opensalt.net/ims/case/v1p0/
No authentication required. No documented rate limits — be respectful.
"""

from __future__ import annotations

import json
import re
import urllib.request
from collections.abc import Iterator
from datetime import date

from ingest_standards.adapters import Adapter
from ingest_standards.models import NodeType, SourceInfo, StandardNode, Subject

BASE_URL = "https://opensalt.net/ims/case/v1p0"

# Known framework identifiers for Indiana standards
FRAMEWORKS = {
    ("math", "2023"): "76673c2e-5cb6-11ee-a3bc-0242c0a84002",
}

# Map OpenSALT educationLevel codes to our grade strings
GRADE_MAP: dict[str, str] = {
    "KG": "K",
    "01": "1",
    "02": "2",
    "03": "3",
    "04": "4",
    "05": "5",
    "06": "6",
    "07": "7",
    "08": "8",
}

# Grades we ingest (K-5)
TARGET_GRADES = {"K", "1", "2", "3", "4", "5"}

# Regex to extract domain from humanCodingScheme
# Math: "K.NS.1" -> grade="K", domain="NS", number="1"
# Process: "PS.1" -> special handling
MATH_CODE_RE = re.compile(r"^([K1-8])\.([A-Z]+)\.(\d+)$")
PROCESS_CODE_RE = re.compile(r"^PS\.(\d+)$")

# Essential marker in fullStatement
ESSENTIAL_SUFFIX = "(E)"


USER_AGENT = "ingest-standards/0.1.0 (homeschool standards tracker; https://github.com)"


def _fetch_json(url: str) -> dict:
    """Fetch JSON from a URL using stdlib only."""
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def _parse_essential(statement: str) -> tuple[str, bool]:
    """Strip the (E) marker and return (clean_text, is_essential)."""
    stripped = statement.strip()
    if stripped.endswith(ESSENTIAL_SUFFIX):
        return stripped[: -len(ESSENTIAL_SUFFIX)].strip(), True
    return stripped, False


class OpenSaltAdapter(Adapter):
    """Fetch math standards from OpenSALT CASE API."""

    def __init__(
        self,
        subject: str = "math",
        version: str = "2023",
        *,
        package_data: dict | None = None,
    ) -> None:
        key = (subject, version)
        if key not in FRAMEWORKS:
            msg = f"No known OpenSALT framework for {subject} {version}"
            raise ValueError(msg)

        self.subject = Subject(subject)
        self.version = version
        self.framework_id = FRAMEWORKS[key]
        self._package_data = package_data

    def _fetch_package(self) -> dict:
        if self._package_data is not None:
            return self._package_data
        url = f"{BASE_URL}/CFPackages/{self.framework_id}"
        return _fetch_json(url)

    def fetch(self) -> Iterator[StandardNode]:
        package = self._fetch_package()
        items: list[dict] = package.get("CFItems", [])
        today = date.today().isoformat()
        source_url = f"{BASE_URL}/CFPackages/{self.framework_id}"

        # First pass: collect domain info (learning outcomes from notes)
        domain_outcomes: dict[str, str] = {}  # "K.NS" -> learning outcome
        for item in items:
            if item.get("CFItemType") == "Domain":
                code = item.get("humanCodingScheme", "")
                notes = item.get("notes", "")
                if code and notes:
                    # Strip "Learning Outcome: " prefix if present
                    outcome = re.sub(r"^Learning Outcome:\s*", "", notes)
                    domain_outcomes[code] = outcome

        # Second pass: yield process standards
        for item in items:
            if item.get("CFItemType") != "Process Standard":
                continue
            code = item.get("humanCodingScheme", "")
            if not code or not PROCESS_CODE_RE.match(code):
                continue

            description, _ = _parse_essential(item.get("fullStatement", ""))
            notes = item.get("notes", "")

            yield StandardNode(
                id=code,
                subject=self.subject,
                grade="all",
                domain="PS",
                type=NodeType.PROCESS,
                description=description,
                learning_outcome=notes if notes else None,
                source=SourceInfo(
                    adapter="opensalt",
                    url=source_url,
                    version=self.version,
                    retrieved=today,
                ),
            )

        # Third pass: yield domain nodes, then standard nodes per grade
        yielded_domains: set[str] = set()

        for item in items:
            item_type = item.get("CFItemType")
            code = item.get("humanCodingScheme", "")
            if not code:
                continue

            if item_type == "Domain":
                m = re.match(r"^([K1-8])\.([A-Z]+)$", code)
                if not m:
                    continue
                grade = "K" if m.group(1) == "K" else m.group(1)
                if grade not in TARGET_GRADES:
                    continue
                domain = m.group(2)
                domain_key = f"{grade}.{domain}"

                if domain_key not in yielded_domains:
                    yielded_domains.add(domain_key)
                    yield StandardNode(
                        id=code,
                        subject=self.subject,
                        grade=grade,
                        domain=domain,
                        type=NodeType.DOMAIN,
                        description=item.get("fullStatement", ""),
                        learning_outcome=domain_outcomes.get(code),
                        source=SourceInfo(
                            adapter="opensalt",
                            url=source_url,
                            version=self.version,
                            retrieved=today,
                        ),
                    )

            elif item_type == "Standard":
                m = MATH_CODE_RE.match(code)
                if not m:
                    continue
                grade = "K" if m.group(1) == "K" else m.group(1)
                if grade not in TARGET_GRADES:
                    continue
                domain = m.group(2)

                description, essential = _parse_essential(
                    item.get("fullStatement", "")
                )
                domain_code = f"{grade}.{domain}"

                yield StandardNode(
                    id=code,
                    subject=self.subject,
                    grade=grade,
                    domain=domain,
                    type=NodeType.STANDARD,
                    description=description,
                    essential=essential,
                    parent_id=domain_code,
                    source=SourceInfo(
                        adapter="opensalt",
                        url=source_url,
                        version=self.version,
                        retrieved=today,
                    ),
                )
