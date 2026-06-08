"""
find_paths.py — author-time script, run manually to regenerate paths.py.

How it works:
  Starting from the root page, we walk the block tree recursively.
  At each level we iterate over sibling blocks, and for each block we build
  a BlockStep that describes how to identify it:
    - block_type: what kind of block it is (toggle, callout, child_database, ...)
    - text:       its plain-text content (empty for columns, column_lists, etc.)
    - index:      its position among siblings of the same block_type at this level

  For each child_database block found, we also probe its sub-resources
  (data sources and views) to discover DS and view IDs.

  All results are written to src/template/paths.py as Python constants.

Usage:
  python -m scripts.find_paths
"""
import json
from collections import defaultdict
from notion_client import Client, collect_paginated_api

from src.config import settings
from src.template.config import template_settings
from src.template.steps import BlockStep, DataSourceStep, ViewStep

OUTPUT_PATH = "src/template/paths.json"


def extract_text(block: dict) -> str:
    block_type = block["type"]
    content = block.get(block_type, {})
    if isinstance(content, dict):
        rich_text = content.get("rich_text", [])
        if rich_text:
            return "".join(rt.get("plain_text", "") for rt in rich_text)
        if "title" in content:
            return content["title"]
    return ""


def probe_database(client: Client, block_id: str, path: tuple, sub_targets: dict) -> dict:
    """Probe a child_database block's data sources and views against sub_targets.

    sub_targets is {normalized_id: label}. Returns {label: path_tuple} for matches.
    """
    found = {}

    db = client.databases.retrieve(database_id=block_id)
    for ds in db.get("data_sources", []):
        ds_id = ds["id"].replace("-", "")
        if ds_id in sub_targets:
            found[sub_targets[ds_id]] = path + (DataSourceStep(name=ds["name"]),)

    for view_stub in client.views.list(database_id=block_id).get("results", []):
        view_id = view_stub["id"].replace("-", "")
        if view_id in sub_targets:
            view = client.views.retrieve(view_id=view_stub["id"])
            found[sub_targets[view_id]] = path + (ViewStep(name=view["name"]),)

    return found


def walk(client: Client, page_id: str, db_targets: dict, sub_targets: dict, current_path: list = None) -> dict:
    """Recursively walk the block tree from page_id.

    db_targets:  {normalized_id: label} for database block IDs.
    sub_targets: {normalized_id: label} for DS and view IDs.

    Returns {label: path_tuple} for all matches found.
    """
    if current_path is None:
        current_path = []

    found = {}
    type_counters = defaultdict(int)
    blocks = collect_paginated_api(client.blocks.children.list, block_id=page_id)

    for block in blocks:
        block_type = block["type"]
        step = BlockStep(block_type=block_type, text=extract_text(block), index=type_counters[block_type])
        path = current_path + [step]

        if block_type == "child_database":
            block_id_norm = block["id"].replace("-", "")
            if block_id_norm in db_targets:
                found[db_targets[block_id_norm]] = tuple(path)
            if sub_targets:
                found.update(probe_database(client, block["id"], tuple(path), sub_targets))

        if block.get("has_children"):
            found.update(walk(client, block["id"], db_targets, sub_targets, path))

        type_counters[block_type] += 1

    return found


def serialize_step(step) -> dict:
    if isinstance(step, BlockStep):
        return {"type": "block", "block_type": step.block_type, "text": step.text, "index": step.index}
    if isinstance(step, DataSourceStep):
        return {"type": "data_source", "name": step.name}
    if isinstance(step, ViewStep):
        return {"type": "view", "name": step.name}
    raise TypeError(f"Unknown step type: {type(step)}")


def generate_paths_file(results: dict) -> None:
    """Write discovered paths as JSON to OUTPUT_PATH."""
    data = {label: [serialize_step(s) for s in path] for label, path in results.items()}
    with open(OUTPUT_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Written {len(results)} paths to {OUTPUT_PATH}")


if __name__ == "__main__":
    def norm(id_str: str) -> str:
        return id_str.replace("-", "")

    db_targets = {
        norm(template_settings.template_tasks_db_id):     "tasks_db",
        norm(template_settings.template_courses_db_id):   "courses_db",
        norm(template_settings.template_semesters_db_id): "semesters_db",
    }

    sub_targets = {
        norm(template_settings.template_tasks_ds_id):          "tasks_ds",
        norm(template_settings.template_courses_ds_id):        "courses_ds",
        norm(template_settings.template_semesters_ds_id):      "semesters_ds",
        norm(template_settings.template_hub_upcoming_view_id): "view_upcoming",
        norm(template_settings.template_hub_calendar_view_id): "view_calendar",
        norm(template_settings.template_hub_courses_view_id):  "view_courses",
    }

    client = Client(auth=settings.notion_access_token)
    results = walk(client, template_settings.root_page_id, db_targets, sub_targets)
    generate_paths_file(results)
