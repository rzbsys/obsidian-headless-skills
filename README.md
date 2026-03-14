# Obsidian Headless Skills

Use Obsidian as an agent-readable knowledge graph and memo layer.

This repository currently contains one skill:

- `obsidian-headless`: sync an Obsidian vault when needed, parse notes and links into a local graph, query backlinks and neighbors, and write memo-style notes back into the vault.

## Install

List the skill first:

```bash
npx -y skills add https://github.com/rzbsys/obsidian-headless-skills --list -a codex
```

Install globally for Codex:

```bash
npx -y skills add https://github.com/rzbsys/obsidian-headless-skills --skill obsidian-headless -a codex -g
```

Install from the direct skill path:

```bash
npx -y skills add https://github.com/rzbsys/obsidian-headless-skills/tree/main/obsidian-headless -a codex -g
```

Restart Codex after installation so the new skill is picked up cleanly.

## What This Skill Does

- Use a local Obsidian vault as the graph source instead of automating the desktop UI.
- Use Obsidian Headless Sync only when the vault must be pulled from Obsidian Sync first.
- Parse Markdown notes, wikilinks, markdown links, tags, aliases, properties, headings, and optional `.base` files.
- Build a note-centric graph artifact for exact lookup, backlinks, and bounded neighbor traversal.
- Create memo-style notes and write them back as plain Markdown plus frontmatter.

## When Obsidian Login Is Required

You do not need to log in to Obsidian if:

- the vault already exists locally, or
- you only want to parse, query, or write notes into a local vault.

You do need Obsidian authentication if:

- the source of truth is an Obsidian Sync vault, and
- you want to pull it onto the current machine with `ob`.

Use one of these:

- `ob login` for interactive setup
- `OBSIDIAN_AUTH_TOKEN` for CI, cron, or server environments

## Quick Start

If the vault is already local, you can go straight to graph building.

Bootstrap a starter config:

```bash
python3 obsidian-headless/scripts/bootstrap_graph_config.py /path/to/vault --output /tmp/graph-config.json
```

Build a graph JSON:

```bash
python3 obsidian-headless/scripts/build_graph_index.py /path/to/vault --config /tmp/graph-config.json --output /tmp/graph.json
```

Inspect a note:

```bash
python3 obsidian-headless/scripts/query_graph.py /tmp/graph.json note "Seed Note"
python3 obsidian-headless/scripts/query_graph.py /tmp/graph.json backlinks "Seed Note"
python3 obsidian-headless/scripts/query_graph.py /tmp/graph.json neighbors "Seed Note" --depth 2
```

Create a quick memo note:

```bash
python3 obsidian-headless/scripts/write_note.py /path/to/vault --memo --body "Remember to revisit [[Projects/Alpha]]"
```

Create a structured note:

```bash
python3 obsidian-headless/scripts/write_note.py /path/to/vault --title "Alpha retro" --folder Meetings --tag project --property status=active --body "Linked to [[Projects/Alpha]]"
```

If the vault is remote-only, sync first with Obsidian Headless and then run the same graph steps on the synced directory.

## Example Prompts

- `Use $obsidian-headless to build a knowledge graph from this vault and show backlinks for [[Alpha]].`
- `Use $obsidian-headless to create a memo note in my vault for today's follow-up items.`
- `옵시디언 vault를 지식 그래프로 읽고 project 태그 노드들만 연결 관계를 보여줘.`
- `메모 노트 하나 만들고 [[Projects/Alpha]]와 연결해줘.`

## Repository Layout

```text
obsidian-headless/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── headless-sync.md
│   └── knowledge-graph-implementation.md
└── scripts/
    ├── bootstrap_graph_config.py
    ├── build_graph_index.py
    ├── obsidian_graph.py
    ├── query_graph.py
    └── write_note.py
```

## Testing

Validate the skill structure:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
python3 "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" ./obsidian-headless
```

Check Python syntax:

```bash
python3 -m py_compile obsidian-headless/scripts/*.py
```

Recommended smoke test:

1. Create a tiny vault with 2-3 linked notes.
2. Run `bootstrap_graph_config.py`.
3. Run `build_graph_index.py`.
4. Run `query_graph.py` for note lookup and backlinks.
5. Run `write_note.py --memo`, then rebuild the graph and confirm the new note appears.

## Design Notes

This README follows the common patterns used by public skills repositories:

- lead with one install command
- explain when the skill is useful
- give a minimal quick start
- keep repository structure visible
- document the human-facing install path separately from the `SKILL.md` agent instructions

The repository is intentionally small. The README is for humans browsing GitHub; the actual agent behavior lives in [`obsidian-headless/SKILL.md`](./obsidian-headless/SKILL.md).
