from dataclasses import dataclass


@dataclass
class WorkspaceConfig:
    tasks_db: str
    courses_db: str
    semesters_db: str
    tasks_ds: str
    courses_ds: str
    semesters_ds: str
    view_upcoming: str
    view_calendar: str
    view_courses: str
