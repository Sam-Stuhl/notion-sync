from dataclasses import dataclass

@dataclass
class TemplateSettings():
    root_page_id: str = "36e4330f6a0481489123f2c0fc7fd207"

    template_courses_db_id: str = "48bde807520f432ba1c43b9ed087b3f8"
    template_tasks_db_id: str = "ea14635db2674e0a8e8ce907adda8f53"
    template_semesters_db_id: str = "0f61f93e91d1420a94c3c14a51b77380"

    template_courses_ds_id: str = "f1901293-287d-4551-99a3-8206234c4188"
    template_tasks_ds_id: str = "e26391e6-ee44-43a6-9f9f-def1e53b7609"
    template_semesters_ds_id: str = "9eafa2a8-910e-48f2-aa3d-d339d981da25"

    template_hub_upcoming_view_id: str = "36e4330f-6a04-8139-b97f-000c8e3becdd"
    template_hub_calendar_view_id: str = "36e4330f-6a04-8116-af68-000c83b0c36d"
    template_hub_courses_view_id: str = "36f4330f-6a04-81ee-b2f1-000cb6447ef5"

template_settings = TemplateSettings()
