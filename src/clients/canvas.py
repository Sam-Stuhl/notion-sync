from canvasapi import Canvas, calendar_event
from datetime import datetime

from src.clients.external_client import ExternalClient, ExternalCourse, ExternalAssignment
from src.config import settings

class CanvasClient(ExternalClient):
    source_name = "Canvas"
    
    def __init__(self):
        self._client = Canvas(settings.canvas_url, settings.canvas_access_token)
        self.user = self._client.get_current_user()
        
    def get_active_courses(self) -> list[ExternalCourse]:
        raw = self._client.get_courses(
            enrollment_state="active",
            include=["term", "syllabus_body", "teachers"],
        )
        return [self._to_course(c) for c in raw]

    def get_assignments(self, course_external_id: str) -> list[ExternalAssignment]:
        course = self._client.get_course(int(course_external_id))
        raw = course.get_assignments(include=["submission"])
        return [self._to_assignment(a, course_external_id) for a in raw]
    
    def get_calendar_events(self, course_ids: list[str]) -> list[calendar_event.CalendarEvent]:
        """Get all calendar events

        Returns:
            list[CalendarEvent]: All calendar events
        """
        context_codes = [f"course_{cid}" for cid in course_ids]
        
        return list(self._client.get_calendar_events(
            context_codes=context_codes,
            all_events=True,
        ))
        
        
    # --- translation helpers ---
    @staticmethod
    def _parse_iso(value):
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _to_course(c) -> ExternalCourse:
        teachers = getattr(c, "teachers", []) or []
        professor = teachers[0].get("display_name") if teachers else None
        term = getattr(c, "term", {}) or {}
        return ExternalCourse(
            id=str(c.id),
            name=c.name,
            code=c.course_code,
            term_name=term.get("name"),
            professor=professor,
            syllabus_html=getattr(c, "syllabus_body", None),
        )

    @staticmethod
    def _to_assignment(a, external_course_id: str) -> ExternalAssignment:
        submission = getattr(a, "submission", None) or {}
        is_submitted = submission.get("workflow_state") in ("submitted", "graded")
        return ExternalAssignment(
            id=str(a.id),
            external_course_id=external_course_id,
            name=a.name,
            due_at=CanvasClient._parse_iso(a.due_at),
            points_possible=a.points_possible,
            description_html=getattr(a, "description", None),
            url=getattr(a, "html_url", None),
            is_submitted=is_submitted,
        )
        
        
        
if __name__ == "__main__":
    canvas = CanvasClient()

    print("=" * 60)
    print("ACTIVE COURSES")
    print("=" * 60)
    courses = canvas.get_active_courses()
    print(f"Found {len(courses)} active courses\n")
    for c in courses:
        print(f"  [{c.id}] {c.name}")
        print(f"    Code: {c.code}")
        print(f"    Term: {c.term_name}")
        print(f"    Professor: {c.professor}")
        print()

    if not courses:
        print("No active courses — skipping assignment and event checks.")
    else:
        first_course = courses[0]

        print("=" * 60)
        print(f"ASSIGNMENTS for {first_course.name}")
        print("=" * 60)
        assignments = canvas.get_assignments(first_course.id)
        print(f"Found {len(assignments)} assignments\n")
        for a in assignments[:5]:
            print(f"  [{a.id}] {a.name}")
            print(f"    Due: {a.due_at}")
            print(f"    Points: {a.points_possible}")
            print(f"    Submitted: {a.is_submitted}")
            print()
        if len(assignments) > 5:
            print(f"  ... and {len(assignments) - 5} more\n")

        print("=" * 60)
        print("CALENDAR EVENTS (all active courses)")
        print("=" * 60)
        events = canvas.get_calendar_events(
            [c.id for c in courses]
        )
        print(f"Found {len(events)} events\n")
        for e in events[:5]:
            print(f"  [{e.id}] {e.title}")
            print(f"    Course: {e.course_external_id}")
            print(f"    Start: {e.start_at}")
            print(f"    Location: {e.location}")
            print()
        if len(events) > 5:
            print(f"  ... and {len(events) - 5} more")