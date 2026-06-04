from canvasapi import Canvas
from canvasapi.course import Course
from canvasapi.assignment import Assignment
from canvasapi.calendar_event import CalendarEvent

from src.config import settings

class CanvasClient:
    def __init__(self):
        self._client = Canvas(settings.canvas_url, settings.canvas_access_token)
        self.user = self._client.get_current_user()
        
    def get_active_courses(self) -> list[Course]:
        """Returns all the active courses

        Returns:
            list[Course]: All active courses
        """
        
        return list(self._client.get_courses(
            enrollment_state="active",
            include=["term", "syllabus_body", "teachers"],
        ))
        
    def get_assignments(self, course_id: str | int) -> list[Assignment]:
        """Returns all assignments for specified course

        Returns:
            list[Assignment]: All assignments for course
        """
        
        course: Course = self._client.get_course(str(course_id), include=["submission"])
        
        return list(course.get_assignments())
    
    def get_calendar_events(self, course_ids: list[str]) -> list[CalendarEvent]:
        """Get all calendar events

        Returns:
            list[CalendarEvent]: All calendar events
        """
        context_codes = [f"course_{cid}" for cid in course_ids]
        
        return list(self._client.get_calendar_events(
            context_codes=context_codes,
            all_events=True,
        ))
        
        
if __name__ == "__main__":
    canvas = CanvasClient()

    courses = canvas.get_active_courses()
    print(f"Found {len(courses)} active courses")
    for c in courses:
        print(f"  {c.id}: {c.name} (term: {getattr(c, 'term', {}).get('name', '?')})")
        
    assignments = canvas.get_assignments(course_id=11907)
    print(f"Found {len(assignments)} assignments")
    for a in assignments[:3]:
        sub_state = a.get_submission(canvas.user) if a.get_submission(canvas.user) else "no submission"
        print(f"  {a.id}: {a.name} due {a.due_at} ({sub_state})")

    events = canvas.get_calendar_events(course_ids=[11907])
    print(f"Found {len(events)} calendar events")