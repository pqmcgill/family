"""Canonical data model for academic standards."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Subject(Enum):
    MATH = "math"
    ELA = "ela"
    SCIENCE = "science"
    SOCIAL_STUDIES = "social_studies"


class NodeType(Enum):
    DOMAIN = "domain"
    STANDARD = "standard"
    SUB_STANDARD = "sub_standard"
    PROCESS = "process"


@dataclass
class SourceInfo:
    adapter: str  # "opensalt" | "pdf" | "csp"
    url: str
    version: str  # e.g., "2023"
    retrieved: str  # ISO date


@dataclass
class ScienceExtensions:
    """NGSS dimensions bundled with each science performance expectation."""

    clarification: str | None = None
    practice: str | None = None  # e.g., "SEP.3"
    practice_name: str | None = None
    core_idea: str | None = None  # e.g., "PS4.A"
    core_idea_name: str | None = None
    crosscutting: str | None = None  # e.g., "CC.2"
    crosscutting_name: str | None = None
    boundary: str | None = None


@dataclass
class StandardNode:
    """Canonical unit of standards data. All adapters produce these."""

    # Identity
    id: str  # e.g., "K.NS.1", "2.W.4a", "1-PS4-1"
    subject: Subject
    grade: str  # "K" | "1" | "2" | ... | "5"
    domain: str  # "NS", "RF", "PS4", "H", etc.
    type: NodeType

    # Content
    description: str
    essential: bool = False

    # Hierarchy
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)

    # Source provenance
    source: SourceInfo = field(default_factory=lambda: SourceInfo("", "", "", ""))

    # Optional metadata
    learning_outcome: str | None = None  # Domain-level learning outcome statement
    sub_domain: str | None = None  # ELA: e.g., "Decoding" under RF
    science: ScienceExtensions | None = None  # Science NGSS dimensions
