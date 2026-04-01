"""CLI entry point for the ingestion pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

from ingest_standards.adapters.opensalt import OpenSaltAdapter
from ingest_standards.emitter import emit_all
from ingest_standards.schema import validate_all
from ingest_standards.validator import validate

# Default output relative to the repo root
DEFAULT_OUTPUT = Path(__file__).resolve().parents[4] / "standards" / "indiana"


def cmd_ingest(output_dir: Path) -> None:
    """Run the OpenSALT ingestion pipeline for math."""
    print(f"Output directory: {output_dir}")
    print()

    print("Fetching Math 2023 from OpenSALT...")
    adapter = OpenSaltAdapter("math", "2023")
    nodes = list(adapter.fetch())
    print(f"  Fetched {len(nodes)} nodes")
    print()

    print("Running structural validation...")
    report = validate(nodes)
    print(report.summary())
    print()

    if report.has_errors:
        print("Validation failed with errors. Not writing files.")
        sys.exit(1)

    print("Writing YAML files...")
    written = emit_all(nodes, output_dir, validation_results=report.to_dict())
    for path in written:
        print(f"  {path}")
    print()
    print("Done.")


def cmd_validate(standards_dir: Path) -> None:
    """Validate all YAML files in the standards directory."""
    print(f"Validating YAML files in: {standards_dir}")
    print()

    reports = validate_all(standards_dir)
    all_passed = True
    for report in reports:
        print(report.summary())
        print()
        if not report.passed:
            all_passed = False

    total_files = len(reports)
    passed = sum(1 for r in reports if r.passed)
    print(f"{passed}/{total_files} files passed schema validation.")

    if not all_passed:
        sys.exit(1)


def cmd_progressions(standards_dir: Path) -> None:
    """Generate the vertical articulation / progressions file."""
    from ingest_standards.progressions import write_progressions

    path = write_progressions(standards_dir)
    print(f"Written: {path}")


def cmd_prompt(subject: str) -> None:
    """Print the extraction prompt for a subject."""
    from ingest_standards.prompts import load_prompt

    prompt = load_prompt(subject)
    print(prompt)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage:")
        print("  ingest-standards ingest [output_dir]      Ingest math from OpenSALT")
        print("  ingest-standards validate [standards_dir]  Validate YAML schema")
        print("  ingest-standards progressions [dir]        Generate domain progressions")
        print("  ingest-standards prompt <subject>          Print PDF extraction prompt")
        print()
        print("Subjects: ela, science, social_studies")
        return

    command = sys.argv[1]

    if command == "ingest":
        output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
        cmd_ingest(output_dir)
    elif command == "progressions":
        standards_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
        cmd_progressions(standards_dir)
    elif command == "validate":
        standards_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
        cmd_validate(standards_dir)
    elif command == "prompt":
        if len(sys.argv) < 3:
            print("Usage: ingest-standards prompt <subject>")
            sys.exit(1)
        cmd_prompt(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
