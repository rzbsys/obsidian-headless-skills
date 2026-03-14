#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from obsidian_graph import parse_scalar, utc_now_iso, write_note


def parse_properties(items: list[str]) -> dict[str, object]:
    properties: dict[str, object] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid property '{item}'. Use key=value.")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid property '{item}'. Key is empty.")
        properties[key] = parse_scalar(value.strip())
    return properties


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a Markdown note inside an Obsidian vault.",
    )
    parser.add_argument("vault", help="Path to the local Obsidian vault")
    parser.add_argument("--title", help="Note title and default filename stem")
    parser.add_argument("--folder", help="Relative folder inside the vault")
    parser.add_argument("--body", help="Note body text")
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read additional body text from stdin",
    )
    parser.add_argument(
        "--memo",
        action="store_true",
        help="Quick memo mode: default folder=Inbox, auto tag=memo, auto created_at, auto title if needed",
    )
    parser.add_argument("--tag", action="append", default=[], help="Repeatable tag")
    parser.add_argument("--alias", action="append", default=[], help="Repeatable alias")
    parser.add_argument(
        "--property",
        action="append",
        default=[],
        help="Repeatable frontmatter property in key=value form",
    )
    parser.add_argument(
        "--heading",
        action="store_true",
        help="Insert '# title' at the top of the body",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the default target path instead of allocating a unique filename",
    )
    parser.add_argument(
        "--output",
        help="Write result JSON to this path instead of stdout",
    )
    args = parser.parse_args()

    stdin_body = sys.stdin.read() if args.stdin else ""
    body_parts = [part for part in [args.body, stdin_body] if part]
    body = "\n\n".join(body_parts).strip()

    title = args.title
    folder = args.folder
    tags = list(args.tag)
    properties = parse_properties(args.property)

    if args.memo:
        if not title:
            title = f"Memo {utc_now_iso().replace(':', '-')}"
        if not folder:
            folder = "Inbox"
        if "memo" not in {tag.lstrip('#').strip() for tag in tags}:
            tags.append("memo")
        properties.setdefault("created_at", utc_now_iso())

    if not title:
        raise SystemExit("--title is required unless --memo is set.")

    result = write_note(
        vault_root=args.vault,
        title=title,
        body=body,
        folder=folder,
        tags=tags,
        aliases=args.alias,
        properties=properties,
        overwrite=args.overwrite,
        include_heading=args.heading,
    )

    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
