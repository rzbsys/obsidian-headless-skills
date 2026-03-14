#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from obsidian_graph import (
    default_bootstrap_config,
    default_graph_config_path,
    default_vault_root,
    discover_vault,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan an Obsidian vault and emit a starter knowledge-graph config.",
    )
    parser.add_argument(
        "vault",
        nargs="?",
        default=str(default_vault_root()),
        help="Path to the local Obsidian vault. Defaults to ~/.obsidian_graph_skills/vault",
    )
    parser.add_argument(
        "--output",
        default=str(default_graph_config_path()),
        help="Write config JSON to this path. Defaults to ~/.obsidian_graph_skills/cache/graph-config.json",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the JSON payload to stdout after writing it to disk",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print discovery summary to stderr",
    )
    args = parser.parse_args()

    config = default_bootstrap_config(args.vault)
    if args.summary:
        summary = discover_vault(args.vault)
        print(json.dumps(summary, indent=2, ensure_ascii=False), file=sys.stderr)

    payload = json.dumps(config, indent=2, ensure_ascii=False) + "\n"
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
                    "output": str(output_path),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
