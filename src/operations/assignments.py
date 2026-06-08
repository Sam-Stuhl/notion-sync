from typing import Optional

from src.clients import notion_props
from src.clients.sis_client import SISAssignment
from src.models import SyncContext


def _sis_assignment_to_notion_props(assignment: SISAssignment, course_notion_id: str, semester_notion_id: Optional[str]) -> dict:
    """Takes in SIS assignment and converts it to a dictionary with the properties of a notion task

    Returns:
        dict: Notion task properties dict
    """
    properties = {
        "Task Name": notion_props.title(assignment.name),
        "Date": notion_props.date(assignment.due_at),
        "Done": notion_props.checkbox(assignment.is_submitted),
        "Kind": notion_props.select("Assignment"),
        "Area": notion_props.select("School"),
        "Course": notion_props.relation([course_notion_id]),
        "Semester": notion_props.relation([semester_notion_id]) if semester_notion_id else None,
    }
    return {k: v for k, v in properties.items() if v is not None}


def sync_assignments(context: SyncContext) -> list[dict]:
    """Discover assignments from all active courses from SIS and upsert into Notion

    Returns:
        list[dict]: A list of dictionaries with the output from being upserted into notion. \nStructure: {"page": properties dict of existing or created page, "was_created": boolean}
    """
    courses = context.external.get_active_courses()

    results = []
    for course in courses:
        results.extend(sync_assignments_for_course(context, course.id))
    return results


def sync_assignments_for_course(context: SyncContext, course_id: str) -> list[dict]:
    """Discover assignments from specified course from SIS and upsert into Notion

    Returns:
        list[dict]: A list of dictionaries with the output from being upserted into notion. \nStructure: {"page": properties dict of existing or created page, "was_created": boolean}
    """
    course_page = context.notion.get_page_by_source(
        context.workspace.template_courses_ds_id,
        context.external.source_name,
        course_id,
    )
    if not course_page:
        return []

    course_notion_id = course_page["id"]
    semester_ids = notion_props.read_relation(course_page["properties"], "Semester")
    semester_notion_id = semester_ids[0] if semester_ids else None

    results = []
    for assignment in context.external.get_assignments(course_id):
        if assignment.is_submitted:
            context.notion.upsert_by_source(
                ds_id=context.workspace.template_tasks_ds_id,
                source=context.external.source_name,
                external_id=assignment.id,
                properties={"Done": notion_props.checkbox(True)},
            )
            continue

        result = context.notion.upsert_by_source(
            ds_id=context.workspace.template_tasks_ds_id,
            source=context.external.source_name,
            external_id=assignment.id,
            properties=_sis_assignment_to_notion_props(assignment, course_notion_id, semester_notion_id),
        )
        results.append(result)

    return results
