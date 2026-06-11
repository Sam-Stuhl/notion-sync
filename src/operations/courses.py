import logging
from typing import Optional

from src.clients import notion_props
from src.clients.sis_client import SISCourse
from src.models import SyncContext
from src.operations.assignments import sync_assignments_for_course

log = logging.getLogger("sync.courses")


# ─── Comparison ───────────────────────────────────────────────────────────────

def _norm_id(page_id: str | None) -> str:
    return (page_id or "").replace("-", "")


def _course_needs_update(
    notion_page: dict,
    course: SISCourse,
    semester_page_id: Optional[str],
) -> bool:
    """Returns True if any Canvas-owned course field differs from current Notion values."""
    props = notion_page["properties"]

    try:
        if notion_props.read_title(props, "Course Name") != course.name:
            return True
    except (KeyError, TypeError):
        return True

    try:
        if notion_props.read_rich_text(props, "Code") != (course.code or ""):
            return True
    except (KeyError, TypeError):
        if course.code:
            return True

    try:
        if notion_props.read_rich_text(props, "Professor") != (course.professor or ""):
            return True
    except (KeyError, TypeError):
        if course.professor:
            return True

    if semester_page_id:
        try:
            rel = notion_props.read_relation(props, "Semester")
            notion_sem = _norm_id(rel[0] if rel else None)
            if notion_sem != _norm_id(semester_page_id):
                return True
        except (KeyError, TypeError):
            return True

    if course.syllabus_html:
        try:
            if (notion_props.read_url(props, "Syllabus") or "") != course.syllabus_html:
                return True
        except (KeyError, TypeError):
            return True

    return False


# ─── Props builder ────────────────────────────────────────────────────────────

def _sis_course_to_notion_props(course: SISCourse, semester_notion_id: Optional[str]) -> dict:
    properties = {
        "Course Name": notion_props.title(course.name),
        "Code": notion_props.rich_text(course.code),
        "Professor": notion_props.rich_text(course.professor) if course.professor else None,
        "Semester": notion_props.relation([semester_notion_id]) if semester_notion_id else None,
        "Syllabus": notion_props.url(course.syllabus_html) if course.syllabus_html else None,
    }
    return {k: v for k, v in properties.items() if v is not None}


def _read_title(page: dict, field: str) -> str:
    try:
        return notion_props.read_title(page["properties"], field) or "Untitled"
    except (KeyError, TypeError):
        return "Untitled"


# ─── Sync ─────────────────────────────────────────────────────────────────────

def sync_courses(context: SyncContext, semester_page_id: Optional[str] = None) -> list[dict]:
    """Upsert active courses. Detects Notion drift; re-creates deleted pages."""
    courses = context.external.get_active_courses()
    existing = context.notion.get_pages_by_source(
        context.workspace.template_courses_ds_id,
        context.external.source_name,
    )
    log.info("fetched %d existing courses from Notion", len(existing))
    source = context.external.source_name
    results = []

    for course in courses:
        props = _sis_course_to_notion_props(course, semester_page_id)
        current = existing.get(course.id)

        if current is None:
            log.info("creating course: %s (%s)", course.name, course.id)
            page = context.notion.create_sourced_page(
                context.workspace.template_courses_ds_id, source, course.id, props
            )
            results.append({"page": page, "was_created": True})
        elif _course_needs_update(current, course, semester_page_id):
            log.info("updating course: %s (%s)", course.name, course.id)
            page = context.notion.update_sourced_page(current["id"], source, course.id, props)
            results.append({"page": page, "was_created": False})
        else:
            log.debug("skipping course (unchanged): %s (%s)", course.name, course.id)

    return results


def sync_courses_and_assignments(
    context: SyncContext, semester_page_id: Optional[str] = None
) -> dict[str, list[dict]]:
    """Sync courses and all their assignments in a single pass.

    Returns:
        {
          "courses":     [{"title": str, "action": "created"|"updated"}, ...],
          "assignments": [{"title": str, "course": str, "action": "created"|"updated"}, ...],
        }
    Only items that were actually written appear in the lists.
    """
    active_courses = context.external.get_active_courses()
    source = context.external.source_name

    # Two bulk fetches — one per database
    existing_courses = context.notion.get_pages_by_source(
        context.workspace.template_courses_ds_id, source
    )
    existing_tasks = context.notion.get_pages_by_source(
        context.workspace.template_tasks_ds_id, source
    )
    log.info(
        "bulk fetch complete: %d courses, %d tasks in Notion",
        len(existing_courses), len(existing_tasks),
    )

    course_items: list[dict] = []
    assignment_items: list[dict] = []

    for course in active_courses:
        props = _sis_course_to_notion_props(course, semester_page_id)
        current = existing_courses.get(course.id)

        if current is None:
            page = context.notion.create_sourced_page(
                context.workspace.template_courses_ds_id, source, course.id, props
            )
            course_notion_id = page["id"]
            course_title = _read_title(page, "Course Name")
            course_items.append({"title": course_title, "action": "created"})
        elif _course_needs_update(current, course, semester_page_id):
            page = context.notion.update_sourced_page(current["id"], source, course.id, props)
            course_notion_id = current["id"]
            course_title = _read_title(page, "Course Name")
            course_items.append({"title": course_title, "action": "updated"})
        else:
            course_notion_id = current["id"]
            course_title = course.name

        # semester_notion_id: use the one we just wrote, or read from existing page
        if semester_page_id:
            semester_notion_id = semester_page_id
        elif current:
            try:
                rel = notion_props.read_relation(current["properties"], "Semester")
                semester_notion_id = rel[0] if rel else None
            except (KeyError, TypeError):
                semester_notion_id = None
        else:
            semester_notion_id = None

        for ar in sync_assignments_for_course(
            context, course.id, existing_tasks, course_notion_id, semester_notion_id
        ):
            item = {
                "title": _read_title(ar["page"], "Task Name"),
                "course": course_title,
                "action": "created" if ar.get("was_created") else "updated",
            }
            if ar.get("reason"):
                item["reason"] = ar["reason"]
            assignment_items.append(item)

    return {"courses": course_items, "assignments": assignment_items}


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
