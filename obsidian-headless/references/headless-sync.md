# Obsidian Headless Sync Ingest Reference

## Use This Reference

- Use this reference only when the user explicitly asks how to configure sync outside the skill.
- Treat Headless Sync as an external ingestion and refresh layer for the knowledge graph.
- After sync is configured elsewhere, operate on local files instead of trying to query the `ob` process directly.

## Official Sources

- Obsidian Headless overview: [https://help.obsidian.md/headless](https://help.obsidian.md/headless)
- Headless Sync guide: [https://help.obsidian.md/sync/headless](https://help.obsidian.md/sync/headless)
- Obsidian Sync overview: [https://help.obsidian.md/sync](https://help.obsidian.md/sync)

## Stable Facts From The Official Docs

- Obsidian Headless is a standalone Obsidian Sync client in open beta.
- Install it with `npm install -g obsidian-headless`.
- Use the `ob` command after installation.
- Require Node.js 22 or later.
- Require an active Obsidian Sync subscription.
- Use `ob login` interactively or `OBSIDIAN_AUTH_TOKEN` for automation.
- Avoid using both the desktop app and Headless Sync on the same device.
- Run sync once with `ob sync` or continuously with `ob sync --continuous`.
- Inspect or tune sync behavior with `ob sync-config`.

## Minimal Ingest Workflow

```shell
npm install -g obsidian-headless
ob login
ob sync-list-remote
mkdir -p ~/.obsidian_graph_skills/vault
ob sync-setup --vault "My Vault" --path ~/.obsidian_graph_skills/vault
ob sync --path ~/.obsidian_graph_skills/vault
```

Use `ob sync --path ~/.obsidian_graph_skills/vault --continuous` only when the agent host is meant to keep a long-running sync worker alive.

## Automation Workflow

```shell
export OBSIDIAN_AUTH_TOKEN="your-token"
mkdir -p ~/.obsidian_graph_skills/vault
ob sync --path ~/.obsidian_graph_skills/vault
```

Run parsing or indexing only after the sync command succeeds.

## Refresh Guidance

- Use one-shot sync before scheduled indexing jobs.
- Use continuous sync only for long-lived agent services that need near-real-time freshness.
- Re-check `ob sync-status --path ...` when the vault appears stale or partially linked.
- Prefer a dedicated path such as `~/.obsidian_graph_skills/vault` instead of the current working directory.
- Do not treat these commands as part of the normal runtime path of this skill; they are external setup and operations steps.

## Troubleshooting Cues

- If `ob` is missing, verify global npm installation and PATH.
- If auth fails in CI or on a server, rotate `OBSIDIAN_AUTH_TOKEN`.
- If sync produces conflicts, verify that the same device is not also running desktop Sync.
- If metadata timestamps differ on Linux, treat birthtime limitations as a platform constraint, not necessarily a sync bug.
