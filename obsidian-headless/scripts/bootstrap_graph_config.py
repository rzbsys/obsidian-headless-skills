#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from obsidian_graph import default_bootstrap_config, discover_vault


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan an Obsidian vault and emit a starter knowledge-graph config.",
    )
    parser.add_argument("vault", help="Path to the local Obsidian vault")
    parser.add_argument(
        "--output",
        help="Write config JSON to this path instead of stdout",
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
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
