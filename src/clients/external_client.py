from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ExternalCourse:
    id: str
    name: str
    code: str
    term_name: Optional[str]
    professor: Optional[str]
    syllabus_html: Optional[str]
    
@dataclass
class ExternalAssignment:
    id: str
    external_course_id: str
    name: str
    due_at: Optional[datetime]
    points_possible: Optional[float]
    description_html: Optional[str]
    url: Optional[str]
    is_submitted: bool
    

class ExternalClient(ABC):
    """Abstract base for SIS clients (Canvas, Brightspace, Banner, etc.).

    Implementations translate their underlying API into these domain types so
    operations stay SIS-agnostic.
    """
    
    source_name: str
    
    @abstractmethod
    def get_active_courses(self) -> list[ExternalCourse]:
        """All courses the user is actively enrolled in."""

    @abstractmethod
    def get_assignments(self, course_external_id: str) -> list[ExternalAssignment]:
        """All assignments for one course, with the user's submission status."""
    