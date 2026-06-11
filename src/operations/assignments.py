import logging
from datetime import datetime, timezone
from typing import Optional

from src.clients import notion_props
from src.clients.sis_client import SISAssignment
from src.models import SyncContext

log = logging.getLogger("sync.assignments")


# ─── Date normalization ────────────────────────────────────────────────────────

def _normalize_dt(dt: datetime | None) -> datetime | None:
    """Normalize to UTC at minute precision — Notion truncates seconds when storing dates."""
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).replace(second=0, microsecond=0)


def _parse_notion_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(second=0, microsecond=0)
    except ValueError:
        return None


def _norm_id(page_id: str | None) -> str:
    return (page_id or "").replace("-", "")


# ─── Comparison ───────────────────────────────────────────────────────────────

def _assignment_update_reason(
    notion_page: dict,
    assignment: SISAssignment,
    course_notion_id: str,
    semester_notion_id: Optional[str],
) -> str | None:
    """Returns all fields that differ as a comma-separated string, or None if up to date."""
    props = notion_page["properties"]
    reasons = []

    # Date
    try:
        notion_date = _parse_notion_dt(notion_props.read_date(props, "Date")[0])
    except (KeyError, TypeError):
        notion_date = None
    canvas_date = _normalize_dt(assignment.due_at)
    if canvas_date != notion_date:
        log.debug("date mismatch  id=%-10s  canvas=%s  notion=%s", assignment.id, canvas_date, notion_date)
        reasons.append("date")

    # Done
    try:
        notion_done = notion_props.read_checkbox(props, "Done")
    except (KeyError, TypeError):
        notion_done = False
    if notion_done != assignment.is_submitted:
        log.debug("done mismatch  id=%-10s  canvas=%s  notion=%s", assignment.id, assignment.is_submitted, notion_done)
        reasons.append("done")

    # Course relation
    try:
        rel = notion_props.read_relation(props, "Course")
        notion_course = _norm_id(rel[0] if rel else None)
    except (KeyError, TypeError):
        notion_course = ""
    canvas_course = _norm_id(course_notion_id)
    if notion_course != canvas_course:
        log.debug("course mismatch  id=%-10s  canvas=%s  notion=%s", assignment.id, canvas_course, notion_course)
        reasons.append("course")

    # Semester relation (only if Canvas has a semester)
    if semester_notion_id:
        try:
            rel = notion_props.read_relation(props, "Semester")
            notion_sem = _norm_id(rel[0] if rel else None)
        except (KeyError, TypeError):
            notion_sem = ""
        canvas_sem = _norm_id(semester_notion_id)
        if notion_sem != canvas_sem:
            log.debug("semester mismatch  id=%-10s  canvas=%s  notion=%s", assignment.id, canvas_sem, notion_sem)
            reasons.append("semester")

    return ", ".join(reasons) if reasons else None


# ─── Props builders ───────────────────────────────────────────────────────────

def _sis_assignment_sync_props(
    assignment: SISAssignment,
    course_notion_id: str,
    semester_notion_id: Optional[str],
) -> dict:
    properties = {
        "Date": notion_props.date(assignment.due_at),
        "Done": notion_props.checkbox(assignment.is_submitted),
        "Kind": notion_props.select("Assignment"),
        "Area": notion_props.select("School"),
        "Course": notion_props.relation([course_notion_id]),
        "Semester": notion_props.relation([semester_notion_id]) if semester_notion_id else None,
    }
    return {k: v for k, v in properties.items() if v is not None}


# ─── Sync ─────────────────────────────────────────────────────────────────────

def sync_assignments(context: SyncContext) -> list[dict]:
    existing_tasks = context.notion.get_pages_by_source(
        context.workspace.template_tasks_ds_id,
        context.external.source_name,
    )
    existing_courses = context.notion.get_pages_by_source(
        context.workspace.template_courses_ds_id,
        context.external.source_name,
    )

    results = []
    for course in context.external.get_active_courses():
        course_page = existing_courses.get(course.id)
        if not course_page:
            log.warning("course %s not found in Notion, skipping assignments", course.id)
            continue
        course_notion_id = course_page["id"]
        try:
            sem = notion_props.read_relation(course_page["properties"], "Semester")
            semester_notion_id = sem[0] if sem else None
        except (KeyError, TypeError):
            semester_notion_id = None

        results.extend(
            sync_assignments_for_course(
                context, course.id, existing_tasks, course_notion_id, semester_notion_id
            )
        )
    return results


def sync_assignments_for_course(
    context: SyncContext,
    course_id: str,
    existing_tasks: dict[str, dict],
    course_notion_id: str,
    semester_notion_id: Optional[str],
) -> list[dict]:
    source = context.external.source_name
    results = []
    skipped = 0

    all_assignments = context.external.get_assignments(course_id)
    log.info(
        "syncing %d assignments for course %s  (existing_tasks_in_map=%d)",
        len(all_assignments), course_id, len(existing_tasks),
    )

    for assignment in all_assignments:
        existing = existing_tasks.get(assignment.id)

        if assignment.is_submitted:
            if existing:
                try:
                    if notion_props.read_checkbox(existing["properties"], "Done"):
                        skipped += 1
                        continue
                except (KeyError, TypeError):
                    pass
                context.notion.update_sourced_page(
                    existing["id"], source, assignment.id,
                    {"Done": notion_props.checkbox(True)},
                )
                log.info("marked done: %s (%s)", assignment.name, assignment.id)
            else:
                context.notion.create_sourced_page(
                    context.workspace.template_tasks_ds_id, source, assignment.id,
                    {
                        "Task Name": notion_props.title(assignment.name),
                        "Done": notion_props.checkbox(True),
                    },
                )
                log.info("created (submitted): %s (%s)", assignment.name, assignment.id)
            continue

        sync_props = _sis_assignment_sync_props(assignment, course_notion_id, semester_notion_id)

        if existing:
            reason = _assignment_update_reason(
                existing, assignment, course_notion_id, semester_notion_id
            )
            if reason is None:
                skipped += 1
                continue
            log.info("updating [%s]: %s (%s)", reason, assignment.name, assignment.id)
            page = context.notion.update_sourced_page(
                existing["id"], source, assignment.id, sync_props
            )
            results.append({"page": page, "was_created": False, "reason": reason})
        else:
            log.info("creating: %s (%s)", assignment.name, assignment.id)
            page = context.notion.create_sourced_page(
                context.workspace.template_tasks_ds_id, source, assignment.id,
                {"Task Name": notion_props.title(assignment.name), **sync_props},
            )
            results.append({"page": page, "was_created": True})

    log.info(
        "course %s: %d updated, %d skipped",
        course_id, len(results), skipped,
    )
    return results
