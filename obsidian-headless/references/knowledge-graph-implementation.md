# Obsidian Knowledge Graph Implementation

## Official Sources

- Obsidian Headless overview: [https://help.obsidian.md/headless](https://help.obsidian.md/headless)
- Headless Sync guide: [https://help.obsidian.md/sync/headless](https://help.obsidian.md/sync/headless)
- Store files in Obsidian: [https://help.obsidian.md/Files+and+folders/How+Obsidian+stores+data](https://help.obsidian.md/Files+and+folders/How+Obsidian+stores+data)
- Internal links: [https://help.obsidian.md/Linking+notes+and+files/Internal+links](https://help.obsidian.md/Linking+notes+and+files/Internal+links)
- Properties: [https://help.obsidian.md/Properties](https://help.obsidian.md/Properties)
- Tags: [https://help.obsidian.md/Tags](https://help.obsidian.md/Tags)
- Graph view: [https://help.obsidian.md/Plugins/Graph+view](https://help.obsidian.md/Plugins/Graph+view)
- Introduction to Bases: [https://help.obsidian.md/bases](https://help.obsidian.md/bases)

## Core Model

Inference from the official docs: the machine-usable graph comes from local vault files, not from the Graph View UI. Obsidian stores notes as Markdown, stores metadata such as properties in frontmatter, supports internal links and tags as first-class note relationships, and visualizes those relationships in Graph View. An external agent can therefore reconstruct a practical knowledge graph directly from the vault filesystem.

## Build The Graph In Layers

### Layer 1: vault snapshot

- Use the local vault if it already exists.
- Otherwise sync it locally with Obsidian Headless.

### Layer 1.5: bootstrap config

- Scan the vault once and persist a small JSON config for repeatable indexing.
- Keep config separate from parser code so folder exclusions and note-resolution rules can evolve without code edits.
- Recommended fields:
  - `vault_root`
  - `exclude_dirs`
  - `note_extensions`
  - `attachment_extensions`
  - `index_frontmatter`
  - `index_inline_tags`
  - `index_bases`
  - `id_strategy`
  - `resolve_order`
  - `folder_hints`

### Layer 2: note parsing

- Parse every `.md` file as one primary note node.
- Extract:
  - filesystem path
  - note title
  - YAML frontmatter properties
  - aliases
  - tags from frontmatter and inline `#tags`
  - headings
  - wikilinks, embeds, and markdown file links

### Layer 3: graph index

- Build `note_id -> note`.
- Build `path`, `title`, and `alias` lookup maps.
- Build outgoing and incoming adjacency lists.
- Build `tag -> notes` and `property key/value -> notes` indexes.

### Layer 4: query surface

- Expose exact note lookup.
- Expose backlinks.
- Expose 1-hop and bounded multi-hop neighbors.
- Expose filtered traversal such as "neighbors of notes tagged `project`".
- Expose contextual expansion around seed notes for answer generation.

## Recommended Schema

### Nodes

- `note`
  - `id`: stable relative path without file extension or another canonical note id
  - `path`
  - `title`
  - `aliases`
  - `tags`
  - `properties`
  - `headings`
  - `mtime`
- `attachment` optional
  - Use only if image or PDF relationships matter
- `tag` optional
  - Keep as a separate node type only when graph traversal across tags is useful

### Edges

- `links_to`
  - Standard wikilink or markdown link to another note
- `embeds`
  - `![[note]]` or embedded file
- `links_heading`
  - Link to `[[note#Heading]]`
- `links_block`
  - Link to `[[note#^block-id]]`
- `tagged_with`
  - Note to tag relationship
- `property_ref` optional
  - Property value points to another note or attachment

Keep the first implementation note-centric. Add heading nodes or block nodes only if retrieval quality requires them.

## Resolve Obsidian-Specific Syntax

### Wikilinks

- Resolve `[[Note]]` by title or canonical path.
- Resolve `[[Note|Alias]]` to the target note and keep the display text separately.
- Resolve `[[Note#Heading]]` as an anchor edge.
- Resolve `[[Note#^block-id]]` as a block-reference edge.

### Markdown links

- Resolve local relative links such as `[text](folder/note.md)`.
- Normalize URL encoding and relative paths before lookup.
- Ignore external `http` or `https` links unless the application needs web edges.

### Tags

- Parse frontmatter tags and inline body tags.
- Normalize tag casing and path style if the application needs consistency.

### Properties

- Parse YAML frontmatter.
- Treat `aliases` and `tags` as special properties because Obsidian uses them directly.
- When a property value looks like an internal note reference, optionally create `property_ref` edges.
- Remember that links inside properties may need quoting in YAML.

### Bases

- Parse `.base` files only when present and relevant.
- Treat them as user-authored structured views over the vault, not as the only source of truth.
- Inference from the official docs: a `.base` file can be mirrored into agent-side filters or saved graph queries without implementing every Bases feature on day one.

## Refresh Strategy

### Simple mode

- Run `ob sync --path ...` if the source is remote.
- Re-scan all Markdown files.
- Rebuild the graph.

### Incremental mode

- Track `mtime`, file creation, deletion, and rename events.
- Re-parse only changed files.
- Recompute inbound resolution for notes whose titles, aliases, or headings changed.

Prefer the simple mode first. Move to incremental indexing only after correctness is proven.

## Bootstrap And Script Pattern

Use this bundled flow for a minimal implementation:

```shell
python3 scripts/bootstrap_graph_config.py /path/to/vault --output /path/to/graph-config.json
python3 scripts/build_graph_index.py /path/to/vault --config /path/to/graph-config.json --output /path/to/graph.json
python3 scripts/query_graph.py /path/to/graph.json note "Seed Note"
```

This pattern keeps the integration transparent:

- bootstrap discovers vault shape
- build creates a deterministic JSON graph artifact
- query validates retrieval and traversal behavior

Once this flow is correct, move the same logic behind an MCP server, API, cron job, or worker process if the agent needs a live service.

## Write-Back Strategy

- Write only supported user-facing artifacts: Markdown, frontmatter, and optionally `.base` files.
- Preserve existing link style where possible.
- When renaming notes, update resolved links or leave a controlled alias strategy.
- Do not write Obsidian cache files as the source of truth.
- Prefer additive writes for capture flows: create a new note in `Inbox/`, `Journal/`, or another agreed folder instead of mutating existing notes by default.
- For quick memo capture, add a lightweight tag such as `memo` and a `created_at` property.

Minimal note-creation pattern:

```shell
python3 scripts/write_note.py /path/to/vault --memo --body "Remember to connect [[Alpha]] with [[Roadmap]]"
python3 scripts/write_note.py /path/to/vault --title "Alpha summary" --folder Inbox --tag project --property source=agent --body "Backlinks: [[Alpha]]"
```

Rebuild the graph after a batch of writes if the agent needs those new notes immediately available for traversal.

## Minimal Architecture

```text
Obsidian Sync or local vault
  -> local filesystem snapshot
  -> markdown/frontmatter parser
  -> link resolver
  -> graph index
  -> agent query tools
  -> optional write-back to markdown
```

## Practical Query Primitives

- `get_note(path_or_title_or_alias)`
- `get_backlinks(note_id)`
- `get_neighbors(note_id, depth=1)`
- `search_by_tag(tag)`
- `search_by_property(key, value)`
- `expand_context(seed_notes, max_hops, filters)`

These primitives are usually enough to support note lookup, neighborhood expansion, and graph-aware retrieval before adding embeddings.

## Implementation Defaults

- Prefer filesystem parsing over browser automation.
- Prefer explicit path-based ids over transient numeric ids.
- Prefer a small deterministic parser and graph index before adding vector search.
- Keep unresolved links visible for debugging and data cleanup.
