from datetime import date
from typing import Optional

from src.clients import notion_props
from src.models import SyncContext
from src.template.config import VIEWS


def get_current_semester(context: SyncContext) -> Optional[str]:
    """Determines what the current semester is based on the semester database

    Returns:
        str: id of the semester page id, or None if no active or upcoming semester found
    """
    _filter = {
        "property": "Dates",
        "date": {"is_not_empty": True}
    }
    _sort = [{"property": "Dates", "direction": "ascending"}]

    semesters = context.notion.query_data_source(
        context.workspace.template_semesters_ds_id, _filter, _sort
    )

    today = date.today()
    fallback_id = None

    for semester in semesters:
        props = semester["properties"]
        start_str, end_str = notion_props.read_date(props, "Dates")

        if not start_str or not end_str:
            continue

        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)

        if start <= today <= end:
            return semester["id"]

        if start > today and fallback_id is None:
            fallback_id = semester["id"]
            break

    return fallback_id


def reconcile_semester_status(context: SyncContext, semester_page_id: str) -> None:
    """Demotes any Current semester (other than the target) to Past, then promotes the target to Current."""

    current_semesters = context.notion.query_data_source(
        context.workspace.template_semesters_ds_id,
        filter_dict={"property": "Status", "select": {"equals": "Current"}},
    )

    for semester in current_semesters:
        if semester["id"] != semester_page_id:
            context.notion.update_page(semester["id"], {"Status": notion_props.select("Past")})

    context.notion.update_page(semester_page_id, {"Status": notion_props.select("Current")})


def update_view_filters(context: SyncContext, semester_page_id: str) -> None:
    """Updates the semester relational filter for the main views on the dashboard"""

    for view in VIEWS:
        semester_condition = {"property": view["semester_prop_id"], "relation": {"contains": semester_page_id}}
        combined_filter = {"and": [*view["base_conditions"], semester_condition]}
        context.notion.update_view(view["view_id"], combined_filter)
