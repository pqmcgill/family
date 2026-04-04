"""Extraction prompt templates for Claude-assisted PDF parsing.

Each prompt is a Jinja-style template with {grade} and {grade_label}
placeholders. The prompts are designed to produce YAML that passes
schema validation (see validator.validate_yaml_schema).
"""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(subject: str) -> str:
    """Load the extraction prompt for a subject."""
    path = PROMPTS_DIR / f"{subject}.md"
    if not path.exists():
        msg = f"No extraction prompt for subject: {subject}"
        raise FileNotFoundError(msg)
    return path.read_text()
