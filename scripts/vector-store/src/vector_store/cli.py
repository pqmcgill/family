"""CLI for the family vector store."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from vector_store.chunker import chunk_file
from vector_store.store import VectorStore, DEFAULT_STORE_PATH

# Directories to scan during rebuild, relative to repo root
REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_DIRS = [
    REPO_ROOT / "data" / "state",
    REPO_ROOT / "data" / "weeks",
    REPO_ROOT / "data" / "edu",
    REPO_ROOT / "standards",
]
DATA_EXTENSIONS = {".yaml", ".yml", ".md"}


def cmd_index(args: argparse.Namespace) -> None:
    """Index a file or directory into the vector store."""
    store = VectorStore(store_path=args.store_path)
    target = Path(args.target).resolve()

    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = [f for f in target.rglob("*") if f.suffix in DATA_EXTENSIONS]
    else:
        print(f"Error: {target} is not a file or directory", file=sys.stderr)
        sys.exit(1)

    total = 0
    for f in sorted(files):
        chunks = chunk_file(f)
        if chunks:
            n = store.upsert(chunks)
            print(f"  {f.relative_to(REPO_ROOT)}: {n} chunks")
            total += n

    print(f"Indexed {total} chunks from {len(files)} files")


def cmd_search(args: argparse.Namespace) -> None:
    """Search the vector store."""
    store = VectorStore(store_path=args.store_path)

    results = store.search(
        query=args.query,
        limit=args.limit,
        filter_type=args.type,
        filter_domain=args.domain,
    )

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print("No results found.")
            return
        for r in results:
            score = f"{r['score']:.4f}" if r['score'] else "n/a"
            print(f"[{score}] {r['source_file']} ({r['type']}/{r['domain']})")
            # Show first 200 chars of text
            text_preview = r["text"][:200].replace("\n", " ")
            print(f"  {text_preview}")
            print()


def cmd_rebuild(args: argparse.Namespace) -> None:
    """Clear and rebuild the entire index from data files."""
    store = VectorStore(store_path=args.store_path)
    store.clear()

    total = 0
    file_count = 0

    for data_dir in DATA_DIRS:
        if not data_dir.exists():
            continue
        files = [f for f in data_dir.rglob("*") if f.suffix in DATA_EXTENSIONS]
        for f in sorted(files):
            chunks = chunk_file(f)
            if chunks:
                n = store.upsert(chunks)
                print(f"  {f.relative_to(REPO_ROOT)}: {n} chunks")
                total += n
                file_count += 1

    print(f"\nRebuilt index: {total} chunks from {file_count} files")


def cmd_status(args: argparse.Namespace) -> None:
    """Show index status."""
    store = VectorStore(store_path=args.store_path)
    info = store.status()

    if info["total_chunks"] == 0:
        print("Vector store is empty. Run `vector-store rebuild` to index data.")
        return

    print(f"Total chunks: {info['total_chunks']}")
    print(f"\nBy type:")
    for t, count in sorted(info["types"].items()):
        print(f"  {t}: {count}")
    print(f"\nSource files ({len(info['source_files'])}):")
    for sf in info["source_files"]:
        try:
            rel = str(Path(sf).relative_to(REPO_ROOT))
        except ValueError:
            rel = sf
        print(f"  {rel}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="vector-store",
        description="Semantic search over family management data",
    )
    parser.add_argument(
        "--store-path",
        type=Path,
        default=DEFAULT_STORE_PATH,
        help="Path to the vector store directory",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # index
    p_index = subparsers.add_parser("index", help="Index a file or directory")
    p_index.add_argument("target", help="File or directory to index")

    # search
    p_search = subparsers.add_parser("search", help="Semantic search")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=10, help="Max results")
    p_search.add_argument("--type", help="Filter by chunk type")
    p_search.add_argument("--domain", help="Filter by domain")
    p_search.add_argument("--json", action="store_true", help="Output as JSON")

    # rebuild
    subparsers.add_parser("rebuild", help="Clear and rebuild the entire index")

    # status
    subparsers.add_parser("status", help="Show index status")

    args = parser.parse_args()

    commands = {
        "index": cmd_index,
        "search": cmd_search,
        "rebuild": cmd_rebuild,
        "status": cmd_status,
    }
    commands[args.command](args)
