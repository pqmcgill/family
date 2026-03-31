"""CLI entry point for the ingestion pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

from ingest_standards.adapters.opensalt import OpenSaltAdapter
from ingest_standards.emitter import emit_all
from ingest_standards.validator import validate

# Default output relative to the repo root
DEFAULT_OUTPUT = Path(__file__).resolve().parents[4] / "standards" / "indiana"


def main() -> None:
    output_dir = DEFAULT_OUTPUT
    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])

    print(f"Output directory: {output_dir}")
    print()

    # Phase 1: Math from OpenSALT
    print("Fetching Math 2023 from OpenSALT...")
    adapter = OpenSaltAdapter("math", "2023")
    nodes = list(adapter.fetch())
    print(f"  Fetched {len(nodes)} nodes")
    print()

    # Validate
    print("Running validation...")
    report = validate(nodes)
    print(report.summary())
    print()

    if report.has_errors:
        print("Validation failed with errors. Not writing files.")
        sys.exit(1)

    # Emit
    print("Writing YAML files...")
    written = emit_all(nodes, output_dir, validation_results=report.to_dict())
    for path in written:
        print(f"  {path}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
