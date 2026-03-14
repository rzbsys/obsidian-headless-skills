#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from obsidian_graph import build_graph, load_config


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a note-centric knowledge graph index from an Obsidian vault.",
    )
    parser.add_argument("vault", help="Path to the local Obsidian vault")
    parser.add_argument(
        "--config",
        help="Optional JSON config emitted by bootstrap_graph_config.py",
    )
    parser.add_argument(
        "--output",
        help="Write graph JSON to this path instead of stdout",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    graph = build_graph(args.vault, config)
    payload = json.dumps(graph, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
