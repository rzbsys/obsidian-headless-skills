#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path


def load_graph(graph_path: str) -> dict:
    return json.loads(Path(graph_path).read_text(encoding="utf-8"))


def build_note_map(graph: dict) -> dict[str, dict]:
    return {note["id"]: note for note in graph.get("notes", [])}


def resolve_note(graph: dict, query: str) -> str | None:
    note_map = build_note_map(graph)
    if query in note_map:
        return query

    normalized = query.strip().lower()
    for note in graph.get("notes", []):
        if note["path"].lower() == normalized or note["title"].lower() == normalized:
            return note["id"]
        aliases = [alias.lower() for alias in note.get("aliases", [])]
        if normalized in aliases:
            return note["id"]

    for index_name in ("paths", "titles", "aliases"):
        ids = graph.get("indexes", {}).get(index_name, {}).get(normalized, [])
        if len(ids) == 1:
            return ids[0]
    return None


def note_view(graph: dict, note_id: str) -> dict:
    note_map = build_note_map(graph)
    note = note_map[note_id]
    return {
        "note": note,
        "backlinks": graph.get("adjacency_in", {}).get(note_id, []),
        "neighbors": graph.get("adjacency_out", {}).get(note_id, []),
    }


def neighbors(graph: dict, note_id: str, depth: int) -> dict:
    adjacency = graph.get("adjacency_out", {})
    visited = {note_id}
    queue: deque[tuple[str, int]] = deque([(note_id, 0)])
    layers: dict[int, list[str]] = {}

    while queue:
        current, current_depth = queue.popleft()
        if current_depth == depth:
            continue
        for target in adjacency.get(current, []):
            if target in visited:
                continue
            visited.add(target)
            next_depth = current_depth + 1
            layers.setdefault(next_depth, []).append(target)
            queue.append((target, next_depth))

    return {
        "seed": note_id,
        "depth": depth,
        "layers": {str(level): nodes for level, nodes in sorted(layers.items())},
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query a graph JSON produced by build_graph_index.py.",
    )
    parser.add_argument("graph", help="Path to graph JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)

    note_parser = subparsers.add_parser("note", help="Resolve and print one note")
    note_parser.add_argument("query", help="Note id, path, title, or alias")

    backlinks_parser = subparsers.add_parser("backlinks", help="List backlinks")
    backlinks_parser.add_argument("query", help="Note id, path, title, or alias")

    neighbors_parser = subparsers.add_parser("neighbors", help="Traverse neighbors")
    neighbors_parser.add_argument("query", help="Note id, path, title, or alias")
    neighbors_parser.add_argument("--depth", type=int, default=1, help="Traversal depth")

    args = parser.parse_args()
    graph = load_graph(args.graph)
    note_id = resolve_note(graph, args.query)
    if not note_id:
        raise SystemExit(f"Could not resolve note: {args.query}")

    if args.command == "note":
        print(json.dumps(note_view(graph, note_id), indent=2, ensure_ascii=False))
        return 0

    if args.command == "backlinks":
        print(
            json.dumps(
                {
                    "note": note_id,
                    "backlinks": graph.get("adjacency_in", {}).get(note_id, []),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "neighbors":
        print(json.dumps(neighbors(graph, note_id, args.depth), indent=2, ensure_ascii=False))
        return 0

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
