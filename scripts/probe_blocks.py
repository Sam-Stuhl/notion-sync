#!/usr/bin/env python3
"""
Probe script: recursively fetches and prints the full block tree of a Notion page as JSON.

Usage (from project root):
    python -m scripts.probe_blocks

Output fields per block:
    id            — Notion block ID
    type          — block type (e.g. "paragraph", "callout", "child_database")
    text          — plain text content, empty string if none
    has_children  — whether the block has child blocks
    depth         — nesting depth from the root page (root children = 0)
    children      — present only when has_children is true; recursively same structure

Purpose: see the raw structural shape of the workspace before designing path-following logic.
No parsing or ID extraction — just a view of the data.
"""
import json
from notion_client import Client, collect_paginated_api
from src.config import settings
from src.template.config import template_settings


def extract_text(block: dict) -> str:
    """Pull plain text from whichever field the block type uses."""
    btype = block["type"]
    content = block.get(btype, {})
    if isinstance(content, dict):
        rich_text = content.get("rich_text", [])
        if rich_text:
            return "".join(rt.get("plain_text", "") for rt in rich_text)
        if "title" in content:
            return content["title"]
    return ""


def fetch_tree(client: Client, block_id: str, depth: int = 0) -> list:
    """Recursively fetch all children of block_id and return as a nested list."""
    blocks = collect_paginated_api(client.blocks.children.list, block_id=block_id)
    result = []
    for block in blocks:
        entry = {
            "id": block["id"],
            "type": block["type"],
            "text": extract_text(block),
            "has_children": block.get("has_children", False),
            "depth": depth,
        }
        if block.get("has_children"):
            entry["children"] = fetch_tree(client, block["id"], depth + 1)
        result.append(entry)
    return result


if __name__ == "__main__":
    client = Client(auth=settings.notion_access_token)
    tree = fetch_tree(client, template_settings.root_page_id)
    print(json.dumps(tree, indent=2))
