from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SISCourse:
    id: str
    name: str
    code: str
    term_name: Optional[str]
    professor: Optional[str]
    syllabus_html: Optional[str]

@dataclass
class SISAssignment:
    id: str
    sis_course_id: str
    name: str
    due_at: Optional[datetime]
    points_possible: Optional[float]
    description_html: Optional[str]
    url: Optional[str]
    is_submitted: bool


class SISClient(ABC):
    """Abstract base for SIS clients (Canvas, Brightspace, Banner, etc.).

    Implementations translate their underlying API into these domain types so
    operations stay SIS-agnostic.
    """

    source_name: str  # Strictly for Notion property naming

    @abstractmethod
    def get_active_courses(self) -> list[SISCourse]:
        """All courses the user is actively enrolled in."""

    @abstractmethod
    def get_assignments(self, course_id: str) -> list[SISAssignment]:
        """All assignments for one course, with the user's submission status."""


_REGISTRY: dict[str, type["SISClient"]] = {}

def register(service: str):
    """Decorator that registers a concrete SISClient under a service name."""
    def decorator(cls: type[SISClient]) -> type[SISClient]:
        _REGISTRY[service] = cls
        return cls
    return decorator

def build(service: str, url: str, token: str) -> SISClient:
    """Instantiate the right SISClient for the given service name."""
    cls = _REGISTRY.get(service)
    if cls is None:
        raise ValueError(f"No client registered for service: {service!r}")
    return cls(url=url, token=token)
