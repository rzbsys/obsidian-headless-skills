#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urldefrag

DEFAULT_EXCLUDE_DIRS = [".obsidian", ".git", "node_modules", ".trash"]
DEFAULT_NOTE_EXTENSIONS = [".md"]
DEFAULT_ATTACHMENT_EXTENSIONS = [
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".pdf",
]

INVALID_FILENAME_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
WIKILINK_RE = re.compile(r"(!)?\[\[([^\]]+)\]\]")
MARKDOWN_LINK_RE = re.compile(r"(!)?\[([^\]]*)\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.MULTILINE)
INLINE_TAG_RE = re.compile(r"(?<![\w/])#([A-Za-z0-9_/-]+)")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_key(value: str) -> str:
    normalized = value.strip().lower().replace("\\", "/")
    return re.sub(r"\s+", " ", normalized)


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def sanitize_filename_component(value: str) -> str:
    cleaned = INVALID_FILENAME_CHARS_RE.sub(" ", value.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    return cleaned or "Untitled"


def safe_note_stem(title: str) -> str:
    return sanitize_filename_component(title)


def sanitize_relative_folder(folder: str | None) -> Path:
    if not folder:
        return Path()
    raw = Path(folder.strip())
    if raw.is_absolute():
        raise ValueError("Folder path must be relative to the vault root.")
    parts = [part for part in raw.parts if part not in ("", ".")]
    if any(part == ".." for part in parts):
        raise ValueError("Folder path must stay inside the vault root.")
    return Path(*parts)


def assert_within_root(root: Path, candidate: Path) -> None:
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Target path escapes the vault root.") from exc


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def render_frontmatter(properties: dict[str, Any]) -> str:
    lines: list[str] = ["---"]
    for key, value in properties.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
                continue
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {yaml_scalar(item)}")
            continue
        lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def allocate_note_path(
    vault_root: Path,
    title: str,
    folder: str | None = None,
    overwrite: bool = False,
) -> Path:
    relative_folder = sanitize_relative_folder(folder)
    target_dir = (vault_root / relative_folder).resolve()
    assert_within_root(vault_root, target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    stem = safe_note_stem(title)
    if overwrite:
        return target_dir / f"{stem}.md"

    candidate = target_dir / f"{stem}.md"
    counter = 2
    while candidate.exists():
        candidate = target_dir / f"{stem} {counter}.md"
        counter += 1
    return candidate


def merge_config(config: dict[str, Any] | None) -> dict[str, Any]:
    merged = {
        "exclude_dirs": list(DEFAULT_EXCLUDE_DIRS),
        "note_extensions": list(DEFAULT_NOTE_EXTENSIONS),
        "attachment_extensions": list(DEFAULT_ATTACHMENT_EXTENSIONS),
        "index_frontmatter": True,
        "index_inline_tags": True,
        "index_bases": True,
        "id_strategy": "relative-path-no-ext",
        "resolve_order": ["path", "title", "alias"],
    }
    if not config:
        return merged
    for key, value in config.items():
        merged[key] = value
    return merged


def load_config(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        return merge_config(None)
    data = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return merge_config(data)


def discover_vault(vault_root: str | Path) -> dict[str, Any]:
    root = Path(vault_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Vault path is not a directory: {root}")

    folder_note_counts: dict[str, int] = defaultdict(int)
    top_level_dirs: list[str] = []
    top_level_files: list[str] = []
    hidden_dirs: list[str] = []
    base_files: list[str] = []
    total_notes = 0

    for entry in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if entry.is_dir():
            top_level_dirs.append(entry.name)
            if entry.name.startswith("."):
                hidden_dirs.append(entry.name)
        elif entry.is_file():
            top_level_files.append(entry.name)

    for path in sorted(root.rglob("*")):
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            suffix = path.suffix.lower()
            if suffix == ".md":
                total_notes += 1
                parent = path.parent.relative_to(root).as_posix()
                folder_note_counts[parent if parent != "." else "/"] += 1
            elif suffix == ".base":
                base_files.append(relative)

    folder_hints = {
        "daily_notes": [],
        "templates": [],
        "archives": [],
    }
    for folder in folder_note_counts:
        normalized = normalize_key(folder)
        if any(token in normalized for token in ("daily", "journal", "journals", "dailies")):
            folder_hints["daily_notes"].append(folder)
        if "template" in normalized:
            folder_hints["templates"].append(folder)
        if any(token in normalized for token in ("archive", "archives")):
            folder_hints["archives"].append(folder)

    return {
        "vault_root": str(root),
        "generated_at": utc_now_iso(),
        "has_obsidian_dir": (root / ".obsidian").is_dir(),
        "top_level_dirs": top_level_dirs,
        "top_level_files": top_level_files,
        "hidden_dirs": hidden_dirs,
        "folder_note_counts": dict(sorted(folder_note_counts.items())),
        "note_count": total_notes,
        "base_files": base_files,
        "folder_hints": folder_hints,
    }


def default_bootstrap_config(vault_root: str | Path) -> dict[str, Any]:
    info = discover_vault(vault_root)
    return {
        "vault_root": info["vault_root"],
        "exclude_dirs": DEFAULT_EXCLUDE_DIRS,
        "note_extensions": DEFAULT_NOTE_EXTENSIONS,
        "attachment_extensions": DEFAULT_ATTACHMENT_EXTENSIONS,
        "index_frontmatter": True,
        "index_inline_tags": True,
        "index_bases": bool(info["base_files"]),
        "id_strategy": "relative-path-no-ext",
        "resolve_order": ["path", "title", "alias"],
        "folder_hints": info["folder_hints"],
        "bootstrap_summary": {
            "note_count": info["note_count"],
            "has_obsidian_dir": info["has_obsidian_dir"],
            "base_files": info["base_files"],
            "top_level_dirs": info["top_level_dirs"],
        },
    }


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    closing = text.find("\n---\n", 4)
    if closing == -1:
        return None, text
    return text[4:closing], text[closing + 5 :]


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.lower() in {"null", "none"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part) for part in inner.split(",")]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_frontmatter_fallback(raw: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^\s+-\s+", line) and current_key:
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(parse_scalar(line.split("-", 1)[1].strip()))
            continue
        if ":" not in line:
            current_key = None
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            current_key = None
            continue
        if value == "":
            data[key] = []
            current_key = key
            continue
        data[key] = parse_scalar(value)
        current_key = None
    return data


def parse_frontmatter(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return parse_frontmatter_fallback(raw)


def as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return dedupe([str(item).strip() for item in value if str(item).strip()])
    if isinstance(value, str):
        if "," in value and "\n" not in value:
            parts = [part.strip() for part in value.split(",")]
            return dedupe([part for part in parts if part])
        return [value.strip()] if value.strip() else []
    return [str(value).strip()]


def frontmatter_tags(properties: dict[str, Any]) -> list[str]:
    tags = as_string_list(properties.get("tags"))
    cleaned: list[str] = []
    for tag in tags:
        cleaned.append(tag[1:] if tag.startswith("#") else tag)
    return dedupe([tag for tag in cleaned if tag])


def frontmatter_aliases(properties: dict[str, Any]) -> list[str]:
    aliases = as_string_list(properties.get("aliases"))
    if not aliases and properties.get("alias"):
        aliases = as_string_list(properties.get("alias"))
    return dedupe([alias for alias in aliases if alias])


def extract_inline_tags(body: str) -> list[str]:
    return dedupe(match.group(1) for match in INLINE_TAG_RE.finditer(body))


def extract_headings(body: str) -> list[dict[str, Any]]:
    headings: list[dict[str, Any]] = []
    for match in HEADING_RE.finditer(body):
        headings.append(
            {
                "level": len(match.group(1)),
                "text": match.group(2).strip(),
            }
        )
    return headings


def extract_wikilinks(body: str) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for match in WIKILINK_RE.finditer(body):
        is_embed = bool(match.group(1))
        raw_target = match.group(2).strip()
        target, display = raw_target, None
        if "|" in raw_target:
            target, display = raw_target.split("|", 1)
        target = target.strip()
        display = display.strip() if display else None
        anchor = None
        link_type = "embeds" if is_embed else "links_to"
        if "#" in target:
            target, anchor = target.split("#", 1)
            if not is_embed:
                link_type = "links_block" if anchor.startswith("^") else "links_heading"
        links.append(
            {
                "syntax": "wikilink",
                "type": link_type,
                "target_raw": raw_target,
                "target": target.strip(),
                "display_text": display,
                "anchor": anchor,
                "is_embed": is_embed,
            }
        )
    return links


def extract_markdown_links(body: str) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for match in MARKDOWN_LINK_RE.finditer(body):
        is_embed = bool(match.group(1))
        display_text = match.group(2).strip() or None
        url = match.group(3).strip()
        if not url:
            continue
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
            continue
        if url.startswith("mailto:"):
            continue
        path_text, fragment = urldefrag(unquote(url))
        link_type = "embeds" if is_embed else "links_to"
        if fragment and not is_embed:
            link_type = "links_block" if fragment.startswith("^") else "links_heading"
        links.append(
            {
                "syntax": "markdown",
                "type": link_type,
                "target_raw": url,
                "target": path_text,
                "display_text": display_text,
                "anchor": fragment or None,
                "is_embed": is_embed,
            }
        )
    return links


def note_id_for(path: Path, vault_root: Path) -> str:
    return path.relative_to(vault_root).with_suffix("").as_posix()


def build_note_indexes(notes: list[dict[str, Any]]) -> dict[str, Any]:
    by_id: dict[str, dict[str, Any]] = {}
    path_map: dict[str, list[str]] = defaultdict(list)
    title_map: dict[str, list[str]] = defaultdict(list)
    alias_map: dict[str, list[str]] = defaultdict(list)

    for note in notes:
        by_id[note["id"]] = note
        relative_path = note["path"]
        without_suffix = note["id"]
        filename = Path(relative_path).stem
        path_variants = {
            normalize_key(relative_path),
            normalize_key(without_suffix),
            normalize_key(filename),
        }
        for variant in path_variants:
            path_map[variant].append(note["id"])
        title_map[normalize_key(note["title"])].append(note["id"])
        for alias in note["aliases"]:
            alias_map[normalize_key(alias)].append(note["id"])

    return {
        "by_id": by_id,
        "path": dict(path_map),
        "title": dict(title_map),
        "alias": dict(alias_map),
    }


def unique_match(candidates: list[str]) -> str | None:
    deduped = dedupe(candidates)
    if len(deduped) == 1:
        return deduped[0]
    return None


def resolve_path_candidate(
    target: str,
    source_path: str,
    vault_root: Path,
    index: dict[str, Any],
) -> str | None:
    normalized = normalize_key(target)
    if normalized in index["path"]:
        return unique_match(index["path"][normalized])

    source_parent = Path(source_path).parent
    relative_candidate = (source_parent / target).as_posix()
    relative_no_ext = Path(relative_candidate).with_suffix("").as_posix()
    for candidate in (
        normalize_key(relative_candidate),
        normalize_key(relative_no_ext),
    ):
        if candidate in index["path"]:
            return unique_match(index["path"][candidate])

    suffix_matches = [
        note_id
        for note_id in index["by_id"]
        if note_id.endswith(normalized) or f"{note_id}.md".endswith(normalized)
    ]
    return unique_match(suffix_matches)


def attachment_match(target: str, source_path: str, vault_root: Path) -> str | None:
    source_parent = Path(source_path).parent
    candidate = (source_parent / target).resolve()
    try:
        return candidate.relative_to(vault_root).as_posix()
    except Exception:
        return None


def resolve_link_target(
    link: dict[str, Any],
    note: dict[str, Any],
    index: dict[str, Any],
    config: dict[str, Any],
    vault_root: Path,
) -> dict[str, Any]:
    target = (link.get("target") or "").strip()
    if not target and link.get("anchor"):
        return {
            "kind": "note",
            "target": note["id"],
        }
    suffix = Path(target).suffix.lower()
    if suffix and suffix in set(config.get("attachment_extensions", [])):
        attachment = attachment_match(target, note["path"], vault_root)
        return {"kind": "attachment", "target": attachment or target}

    resolution_order = config.get("resolve_order", ["path", "title", "alias"])
    for strategy in resolution_order:
        if strategy == "path":
            resolved = resolve_path_candidate(target, note["path"], vault_root, index)
            if resolved:
                return {"kind": "note", "target": resolved}
        elif strategy == "title":
            resolved = unique_match(index["title"].get(normalize_key(target), []))
            if resolved:
                return {"kind": "note", "target": resolved}
        elif strategy == "alias":
            resolved = unique_match(index["alias"].get(normalize_key(target), []))
            if resolved:
                return {"kind": "note", "target": resolved}

    attachment = attachment_match(target, note["path"], vault_root)
    if attachment and Path(attachment).suffix.lower() in set(config.get("attachment_extensions", [])):
        return {"kind": "attachment", "target": attachment}
    return {"kind": "unresolved", "target": target}


def property_index_for(notes: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    index: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for note in notes:
        for key, value in note["properties"].items():
            if isinstance(value, list):
                scalar_values = [str(item).strip() for item in value if str(item).strip()]
            elif isinstance(value, (str, int, bool)):
                scalar_values = [str(value).strip()]
            else:
                continue
            for scalar in scalar_values:
                index[key][scalar].append(note["id"])
    return {
        key: {value: dedupe(ids) for value, ids in values.items()}
        for key, values in index.items()
    }


def iter_note_files(vault_root: Path, config: dict[str, Any]) -> list[Path]:
    note_exts = {suffix.lower() for suffix in config.get("note_extensions", DEFAULT_NOTE_EXTENSIONS)}
    exclude_dirs = set(config.get("exclude_dirs", DEFAULT_EXCLUDE_DIRS))
    files: list[Path] = []
    for current_root, dirs, filenames in os.walk(vault_root):
        dirs[:] = sorted(name for name in dirs if name not in exclude_dirs)
        for filename in sorted(filenames):
            path = Path(current_root, filename)
            if path.suffix.lower() in note_exts:
                files.append(path)
    return files


def parse_note(path: Path, vault_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    raw_frontmatter, body = split_frontmatter(text)
    properties = parse_frontmatter(raw_frontmatter) if config.get("index_frontmatter", True) else {}
    aliases = frontmatter_aliases(properties)
    tags = frontmatter_tags(properties)
    if config.get("index_inline_tags", True):
        tags = dedupe(tags + extract_inline_tags(body))
    headings = extract_headings(body)
    raw_links = extract_wikilinks(body) + extract_markdown_links(body)
    note_id = note_id_for(path, vault_root)
    stat = path.stat()
    return {
        "id": note_id,
        "path": path.relative_to(vault_root).as_posix(),
        "title": path.stem,
        "display_title": str(properties.get("title")).strip()
        if isinstance(properties.get("title"), str)
        else path.stem,
        "aliases": aliases,
        "tags": tags,
        "properties": properties,
        "headings": headings,
        "raw_links": raw_links,
        "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat(),
    }


def write_note(
    vault_root: str | Path,
    title: str,
    body: str = "",
    folder: str | None = None,
    tags: list[str] | None = None,
    aliases: list[str] | None = None,
    properties: dict[str, Any] | None = None,
    overwrite: bool = False,
    include_heading: bool = False,
) -> dict[str, Any]:
    root = Path(vault_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Vault path is not a directory: {root}")

    tags = dedupe([tag.lstrip("#").strip() for tag in (tags or []) if tag.strip()])
    aliases = dedupe([alias.strip() for alias in (aliases or []) if alias.strip()])
    merged_properties = dict(properties or {})

    existing_tags = frontmatter_tags(merged_properties)
    existing_aliases = frontmatter_aliases(merged_properties)
    if tags:
        merged_properties["tags"] = dedupe(existing_tags + tags)
    elif "tags" in merged_properties and not existing_tags:
        merged_properties.pop("tags", None)

    if aliases:
        merged_properties["aliases"] = dedupe(existing_aliases + aliases)
    elif "aliases" in merged_properties and not existing_aliases:
        merged_properties.pop("aliases", None)

    path = allocate_note_path(root, title=title, folder=folder, overwrite=overwrite)
    frontmatter = render_frontmatter(merged_properties) if merged_properties else ""
    normalized_body = body.rstrip("\n")
    if include_heading:
        heading = f"# {title}".rstrip()
        if normalized_body:
            normalized_body = f"{heading}\n\n{normalized_body}"
        else:
            normalized_body = heading

    parts = []
    if frontmatter:
        parts.append(frontmatter)
    if normalized_body:
        parts.append(normalized_body)
    text = "\n\n".join(parts).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")

    note = parse_note(path, root, merge_config(None))
    return {
        "path": str(path),
        "relative_path": path.relative_to(root).as_posix(),
        "note_id": note["id"],
        "title": title,
        "tags": note["tags"],
        "aliases": note["aliases"],
        "properties": note["properties"],
    }


def build_graph(vault_root: str | Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    root = Path(vault_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Vault path is not a directory: {root}")

    merged_config = merge_config(config)
    note_files = iter_note_files(root, merged_config)
    notes = [parse_note(path, root, merged_config) for path in note_files]
    index = build_note_indexes(notes)

    edges: list[dict[str, Any]] = []
    note_edges: list[dict[str, Any]] = []
    attachment_edges: list[dict[str, Any]] = []
    unresolved_links: list[dict[str, Any]] = []
    adjacency_out: dict[str, list[str]] = defaultdict(list)
    adjacency_in: dict[str, list[str]] = defaultdict(list)
    tag_index: dict[str, list[str]] = defaultdict(list)

    for note in notes:
        for tag in note["tags"]:
            tag_index[tag].append(note["id"])
        for link in note["raw_links"]:
            resolved = resolve_link_target(link, note, index, merged_config, root)
            edge = {
                "source": note["id"],
                "type": link["type"],
                "syntax": link["syntax"],
                "target_raw": link["target_raw"],
                "display_text": link["display_text"],
                "anchor": link["anchor"],
            }
            edge.update(resolved)
            edges.append(edge)
            if resolved["kind"] == "note":
                note_edges.append(edge)
                adjacency_out[note["id"]].append(resolved["target"])
                adjacency_in[resolved["target"]].append(note["id"])
            elif resolved["kind"] == "attachment":
                attachment_edges.append(edge)
            else:
                unresolved_links.append(edge)

    cleaned_notes = []
    for note in notes:
        cleaned_note = dict(note)
        cleaned_note.pop("raw_links", None)
        cleaned_note["outgoing_note_count"] = len(adjacency_out.get(note["id"], []))
        cleaned_note["incoming_note_count"] = len(adjacency_in.get(note["id"], []))
        cleaned_notes.append(cleaned_note)

    return {
        "metadata": {
            "vault_root": str(root),
            "generated_at": utc_now_iso(),
            "builder": "obsidian-headless",
        },
        "config": merged_config,
        "summary": {
            "note_count": len(cleaned_notes),
            "edge_count": len(edges),
            "note_edge_count": len(note_edges),
            "attachment_edge_count": len(attachment_edges),
            "unresolved_link_count": len(unresolved_links),
            "tag_count": len(tag_index),
            "property_key_count": len(property_index_for(cleaned_notes)),
        },
        "notes": cleaned_notes,
        "note_edges": note_edges,
        "attachment_edges": attachment_edges,
        "unresolved_links": unresolved_links,
        "adjacency_out": {key: dedupe(value) for key, value in adjacency_out.items()},
        "adjacency_in": {key: dedupe(value) for key, value in adjacency_in.items()},
        "indexes": {
            "tags": {tag: dedupe(note_ids) for tag, note_ids in tag_index.items()},
            "properties": property_index_for(cleaned_notes),
            "titles": {
                key: dedupe(value)
                for key, value in index["title"].items()
            },
            "aliases": {
                key: dedupe(value)
                for key, value in index["alias"].items()
            },
            "paths": {
                key: dedupe(value)
                for key, value in index["path"].items()
            },
        },
    }
