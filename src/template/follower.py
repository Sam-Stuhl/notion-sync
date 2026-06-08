"""
follower.py — runtime path executor.

Loads paths.json and executes each path against a user's root page ID
to discover their workspace IDs. Called once at template duplication/onboarding.

Entry point: discover_workspace(client, root_page_id) -> WorkspaceConfig
"""
import json
from collections import defaultdict
from pathlib import Path
from notion_client import Client, collect_paginated_api

from src.template.steps import BlockStep, DataSourceStep, ViewStep
from src.template.models import WorkspaceConfig

PATHS_FILE = Path(__file__).parent / "paths.json"


def _load_paths() -> dict:
    """Deserialize paths.json into {label: tuple[step, ...]}."""
    with open(PATHS_FILE) as f:
        raw = json.load(f)

    paths = {}
    for label, steps_data in raw.items():
        steps = []
        for s in steps_data:
            if s["type"] == "block":
                steps.append(BlockStep(block_type=s["block_type"], text=s["text"], index=s["index"]))
            elif s["type"] == "data_source":
                steps.append(DataSourceStep(name=s["name"]))
            elif s["type"] == "view":
                steps.append(ViewStep(name=s["name"]))
        paths[label] = tuple(steps)
    return paths


def _extract_text(block: dict) -> str:
    block_type = block["type"]
    content = block.get(block_type, {})
    if isinstance(content, dict):
        rich_text = content.get("rich_text", [])
        if rich_text:
            return "".join(rt.get("plain_text", "") for rt in rich_text)
        if "title" in content:
            return content["title"]
    return ""


def _follow_block_step(client: Client, current_id: str, step: BlockStep) -> str:
    blocks = collect_paginated_api(client.blocks.children.list, block_id=current_id)
    type_counter = 0
    for block in blocks:
        if block["type"] != step.block_type:
            continue
        if step.text:
            if _extract_text(block) == step.text:
                return block["id"]
        else:
            if type_counter == step.index:
                return block["id"]
        type_counter += 1
    raise RuntimeError(f"No match for {step} under block {current_id}")


def _follow_ds_step(client: Client, current_id: str, step: DataSourceStep) -> str:
    db = client.databases.retrieve(database_id=current_id)
    for ds in db.get("data_sources", []):
        if ds["name"] == step.name:
            return ds["id"]
    raise RuntimeError(f"No data source named {step.name!r} in database {current_id}")


def _follow_view_step(client: Client, current_id: str, step: ViewStep) -> str:
    for view_stub in collect_paginated_api(client.views.list, database_id=current_id):
        view = client.views.retrieve(view_id=view_stub["id"])
        if view.get("name") == step.name:
            return view["id"]
    raise RuntimeError(f"No view named {step.name!r} in database {current_id}")


def follow_path(client: Client, root_page_id: str, steps: tuple) -> str:
    """Execute a step sequence from root_page_id and return the discovered ID."""
    current_id = root_page_id
    for step in steps:
        if isinstance(step, BlockStep):
            current_id = _follow_block_step(client, current_id, step)
        elif isinstance(step, DataSourceStep):
            current_id = _follow_ds_step(client, current_id, step)
        elif isinstance(step, ViewStep):
            current_id = _follow_view_step(client, current_id, step)
    return current_id


def discover_workspace(client: Client, root_page_id: str) -> WorkspaceConfig:
    """Execute all paths against root_page_id and return a WorkspaceConfig."""
    paths = _load_paths()
    ids = {label: follow_path(client, root_page_id, steps) for label, steps in paths.items()}
    return WorkspaceConfig(**ids)
