from typing import Optional

from src.clients import notion_props
from src.clients.external_client import ExternalClient, ExternalAssignment
from src.clients.notion import NotionClient
from src.config import settings


# --- Helpers ---

def _external_assignment_to_notion_props(ex_assignment: ExternalAssignment, course_notion_id: str, semester_notion_id: Optional[str]) -> dict:
    """Takes in external assignment and converts it to a dictionary with the properties of a notion task

    Returns:
        dict: Notion task properties dict
    """
    properties = {
        "Task Name": notion_props.title(ex_assignment.name),
        "Date": notion_props.date(ex_assignment.due_at),
        "Done": notion_props.checkbox(ex_assignment.is_submitted),
        "Kind": notion_props.select("Assignment"),
        "Area": notion_props.select("School"),
        "Course": notion_props.relation([course_notion_id]),
        "Semester": notion_props.relation([semester_notion_id]) if semester_notion_id else None,
    }
    return {k: v for k, v in properties.items() if v is not None}


# --- Main ---

def sync_assignments(external: ExternalClient, notion: NotionClient) -> list[dict]:
    """Discover assignments from all active courses from external connection and upsert into notion

    Returns:
        list[dict]: A list of dictionaries with the output from being upserted into notion. \nStructure: {"page": properties dict of existing or created page, "was_created": boolean}
    """
    ex_courses = external.get_active_courses()

    results = []
    for course in ex_courses:
        results.extend(sync_assignments_for_course(external, notion, course.id))
    return results


def sync_assignments_for_course(external: ExternalClient, notion: NotionClient, course_id: str, semester_notion_id: Optional[str] = None) -> list[dict]:
    """Discover assignments from specified course from external connection and upsert into notion

    Returns:
        list[dict]: A list of dictionaries with the output from being upserted into notion. \nStructure: {"page": properties dict of existing or created page, "was_created": boolean}
    """
    course_page = notion.get_page_by_source(settings.notion_courses_ds_id, external.source_name, course_id)
    if not course_page:
        return []
    course_notion_id = course_page["id"]

    results = []
    for assignment in external.get_assignments(course_id):
        if assignment.is_submitted:
            notion.upsert_by_source(
                ds_id=settings.notion_tasks_ds_id,
                source=external.source_name,
                external_id=assignment.id,
                properties={"Done": notion_props.checkbox(True)},
            )
            continue

        result = notion.upsert_by_source(
            ds_id=settings.notion_tasks_ds_id,
            source=external.source_name,
            external_id=assignment.id,
            properties=_external_assignment_to_notion_props(assignment, course_notion_id, semester_notion_id),
        )
        results.append(result)

    return results
    
