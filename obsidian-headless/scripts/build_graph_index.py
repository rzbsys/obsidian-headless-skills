#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from obsidian_graph import (
    build_graph,
    default_graph_config_path,
    default_graph_path,
    default_vault_root,
    load_config,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a note-centric knowledge graph index from an Obsidian vault.",
    )
    parser.add_argument(
        "vault",
        nargs="?",
        default=str(default_vault_root()),
        help="Path to the local Obsidian vault. Defaults to ~/.obsidian_graph_skills/vault",
    )
    parser.add_argument(
        "--config",
        default=str(default_graph_config_path()),
        help="Config JSON path. Defaults to ~/.obsidian_graph_skills/cache/graph-config.json",
    )
    parser.add_argument(
        "--output",
        default=str(default_graph_path()),
        help="Write graph JSON to this path. Defaults to ~/.obsidian_graph_skills/cache/graph.json",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the graph JSON to stdout after writing it to disk",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    graph = build_graph(args.vault, config)
    payload = json.dumps(graph, indent=2, ensure_ascii=False) + "\n"
    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(payload, encoding="utf-8")
    if args.stdout:
        print(payload, end="")
    else:
        print(
            json.dumps(
                {
                    "vault": str(Path(args.vault).expanduser()),
                    "config": str(Path(args.config).expanduser()),
                    "output": str(output_path),
                    "summary": graph.get("summary", {}),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
