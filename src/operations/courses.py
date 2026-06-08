from typing import Optional

from src.clients import notion_props
from src.clients.sis_client import SISCourse
from src.models import SyncContext
from src.operations.assignments import sync_assignments_for_course


def _sis_course_to_notion_props(course: SISCourse, semester_notion_id: Optional[str]) -> dict:
    """Takes in SIS course and converts it to a dictionary with the properties of a notion course

    Returns:
        dict: Notion Course properties dict
    """
    properties = {
        "Course Name": notion_props.title(course.name),
        "Code": notion_props.rich_text(course.code),
        "Professor": notion_props.rich_text(course.professor) if course.professor else None,
        "Semester": notion_props.relation([semester_notion_id]) if semester_notion_id else None,
        "Syllabus": notion_props.url(course.syllabus_html) if course.syllabus_html else None,
    }
    return {k: v for k, v in properties.items() if v is not None}


def sync_courses(context: SyncContext, semester_page_id: Optional[str] = None, sync_assignments: bool = True) -> list[dict]:
    """Discover Courses from SIS and upsert into Notion

    Returns:
        list[dict]: A list of dictionaries with the output from being upserted into notion. \nStructure: {"page": properties dict of existing or created page, "was_created": boolean}
    """
    courses = context.external.get_active_courses()

    results = []
    for course in courses:
        result = context.notion.upsert_by_source(
            ds_id=context.workspace.template_courses_ds_id,
            source=context.external.source_name,
            external_id=course.id,
            properties=_sis_course_to_notion_props(course, semester_page_id),
        )
        results.append(result)

        if sync_assignments:
            sync_assignments_for_course(context, course.id)

    return results


if __name__ == "__main__":
    from src.clients.canvas import CanvasClient
    from src.clients.notion import NotionClient
    from src.template.config import template_settings
    from src.models import SyncContext

    context = SyncContext(
        external=CanvasClient(),
        notion=NotionClient(),
        workspace=template_settings,
    )
    results = sync_courses(context)
    for r in results:
        print(f"  {'+' if r['was_created'] else '·'} {notion_props.read_title(r['page']['properties'], 'Course Name')}")
