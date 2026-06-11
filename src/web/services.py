from dataclasses import dataclass


@dataclass
class ServiceDefinition:
    id: str
    name: str
    icon: str
    description: str
    status: str  # "available" | "coming_soon"
    form_template: str | None
    auth_type: str  # "token" | "oauth"


SERVICES: list[ServiceDefinition] = [
    ServiceDefinition(
        id="canvas",
        name="Canvas",
        icon="graduation-cap",
        description="Sync LMS assignments and courses",
        status="available",
        form_template="integrations/forms/canvas.html",
        auth_type="token",
    ),
    ServiceDefinition(
        id="brightspace",
        name="Brightspace",
        icon="book-open",
        description="Sync D2L Brightspace assignments and courses",
        status="coming_soon",
        form_template=None,
        auth_type="token",
    ),
    # ServiceDefinition(
    #     id="google_calendar",
    #     name="Google Calendar",
    #     icon="calendar-days",
    #     description="Sync calendar events into Notion",
    #     status="coming_soon",
    #     form_template=None,
    #     auth_type="oauth",
    # ),
    # ServiceDefinition(
    #     id="gmail",
    #     name="Gmail",
    #     icon="mail",
    #     description="Sync emails and threads into Notion",
    #     status="coming_soon",
    #     form_template=None,
    #     auth_type="oauth",
    # ),
]

SERVICES_BY_ID: dict[str, ServiceDefinition] = {s.id: s for s in SERVICES}
