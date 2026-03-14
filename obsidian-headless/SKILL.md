---
name: obsidian-headless
description: Use Obsidian vaults as an agent-readable knowledge graph by syncing a vault with Obsidian Headless (`obsidian-headless`, `ob`) when needed and then parsing notes, links, tags, properties, and related metadata from the local filesystem. Use when Codex needs to build, query, refresh, or write back to an Obsidian-based memory layer, personal knowledge base, RAG corpus, backlink graph, note relationship graph, or memo capture flow. Trigger on requests such as "use Obsidian as a knowledge graph", "sync vault for an agent", "parse Obsidian links/properties", "create a note in my vault", "headless sync for AI", or Korean requests like "옵시디언을 지식 그래프로", "obsidian headless로 에이전트 메모리", "vault를 그래프로 읽기", or "메모 노트 만들어줘". Do not use this skill for Obsidian CLI or desktop-app control tasks.
---

# Obsidian Headless

## Overview

Use Obsidian Headless as a vault access layer and the vault filesystem as the actual graph source. Build the agent's knowledge graph from Markdown files, internal links, tags, and properties instead of trying to automate the Obsidian desktop UI.

Read [references/knowledge-graph-implementation.md](references/knowledge-graph-implementation.md) for graph modeling and implementation details. Read [references/headless-sync.md](references/headless-sync.md) only when the vault must be synced locally first.

## Match The Request

- Use this skill for agent memory, knowledge graph, vault parsing, backlink traversal, graph-aware retrieval, memo note creation, and headless vault sync.
- Treat Obsidian Headless as an ingestion or refresh mechanism, not as the graph itself.
- Skip Headless entirely when the vault already exists on local disk and is current enough to parse directly.
- Decline desktop-app automation and do not explain Obsidian CLI workflows here.

## Choose The Access Path

### Use direct filesystem access

- Use direct file access when the vault is already present on disk.
- Parse `.md`, frontmatter, `.obsidian/`, and optional `.base` files directly.
- Prefer this path for local agents, indexing jobs, and offline analysis.

### Use Headless Sync first

- Use Headless Sync when the vault lives in Obsidian Sync and the agent host needs a local copy.
- Sync to a working directory, then parse the resulting files as a normal vault.
- Re-run `ob sync` or `ob sync --continuous` before indexing when freshness matters.

## Bootstrap The Agent Graph

- On first use, scan the vault and write a small JSON config instead of hard-coding assumptions.
- Keep the config outside `.obsidian` unless the user explicitly wants it synced with the vault.
- Capture:
  - vault root
  - excluded directories such as `.obsidian`, `.git`, and `node_modules`
  - whether `.base` files exist
  - likely daily-note, template, and archive folders
  - note id strategy and link resolution order
- Prefer the bundled bootstrap script for this first pass:

```shell
python3 scripts/bootstrap_graph_config.py /path/to/vault --output /path/to/graph-config.json
```

- Review the generated config before building the graph. Tighten `exclude_dirs` and folder hints if the vault has unusual structure.

## Follow This Workflow

### 1. Acquire a local vault snapshot

- Confirm the vault path.
- If the vault is remote-only, sync it locally with Obsidian Headless.
- Keep secrets out of logs and replies.

### 2. Build graph primitives

- Create one primary node per note file.
- Extract note title, path, aliases, tags, properties, headings, and outbound links.
- Resolve wikilinks, markdown links, heading references, block references, and embeds.
- Track unresolved links separately instead of dropping them.

### 3. Build graph indexes

- Build `path -> note`, `title -> note`, and `alias -> note` indexes.
- Build outgoing and incoming adjacency lists.
- Build tag and property indexes for structured filtering.
- Keep heading or block anchors only if retrieval needs section-level precision.
- Prefer the bundled index builder for the first implementation:

```shell
python3 scripts/build_graph_index.py /path/to/vault --config /path/to/graph-config.json --output /path/to/graph.json
```

### 4. Expose query operations

- Support exact note lookup by path, title, or alias.
- Support backlinks, neighbors, and bounded multi-hop traversal.
- Support tag and property filtering before graph expansion.
- Support "expand around seed notes" retrieval for answer generation.
- Use the bundled query helper for quick inspection:

```shell
python3 scripts/query_graph.py /path/to/graph.json note "Seed Note"
python3 scripts/query_graph.py /path/to/graph.json backlinks "Seed Note"
python3 scripts/query_graph.py /path/to/graph.json neighbors "Seed Note" --depth 2
```

### 5. Refresh safely

- Refresh by syncing first when the source of truth is remote.
- Re-index incrementally by changed files when possible.
- Fall back to a full rebuild when link resolution or aliases changed broadly.

### 6. Write back carefully

- Write plain Markdown and frontmatter, not app-private cache state.
- Preserve user formatting, headings, and existing wikilink style.
- Avoid destructive renames unless link updates are also handled.
- Prefer creating new notes in a dedicated folder such as `Inbox/` for quick captures and memos.
- Use the bundled note writer for simple capture flows:

```shell
python3 scripts/write_note.py /path/to/vault --memo --body "Remember to revisit the Alpha design"
python3 scripts/write_note.py /path/to/vault --title "Alpha retro" --folder Meetings --tag project --property status=active --body "Linked to [[Projects/Alpha]]"
```

## Use These Defaults

- Treat Markdown files as the canonical source of graph data.
- Treat Obsidian Graph View as a visualization, not as the integration surface.
- Prefer a filesystem parser plus a small graph index over browser automation.
- Add vector search only as a secondary retrieval layer. Keep graph traversal available for symbolic relationships.
- Parse `.base` files only when the vault uses Bases and the agent needs those saved views.
- Start with a JSON config and JSON graph artifact before moving to a database or service.

## Bundled Scripts

- `scripts/bootstrap_graph_config.py`: scan a vault and emit a starter graph config.
- `scripts/build_graph_index.py`: parse notes, resolve links, and emit a note-centric graph JSON.
- `scripts/query_graph.py`: inspect one note, backlinks, and bounded neighbors from a built graph.
- `scripts/write_note.py`: create a new Markdown note or quick memo inside the vault.
- `scripts/obsidian_graph.py`: shared parsing and graph-building utilities used by the entrypoint scripts.

## Answering Guidance

- Separate the answer into access, parse, index, query, and refresh steps when describing an implementation.
- Recommend the simplest viable architecture first: sync or read locally, parse Markdown, build adjacency lists, expose graph queries.
- Call out when a statement is an inference from the official docs rather than an explicitly documented API contract.
- Use [references/headless-sync.md](references/headless-sync.md) for exact `ob` commands and [references/knowledge-graph-implementation.md](references/knowledge-graph-implementation.md) for graph schema and parser guidance.
