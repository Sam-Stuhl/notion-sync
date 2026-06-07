from typing import Optional

from src.clients import notion_props
from src.clients.notion import NotionClient
from src.clients.external_client import ExternalClient, ExternalCourse
from src.config import settings
from src.operations.assignments import sync_assignments_for_course

# --- Helpers ---

def _external_course_to_notion_props(ex_course: ExternalCourse, semester_notion_id: Optional[str]) -> dict:
    """Takes in external course and converts it to a dictionary with the properties of a notion course

    Returns:
        dict: Notion Course properties dict
    """
    properties = {
        "Course Name": notion_props.title(ex_course.name),
        "Code": notion_props.rich_text(ex_course.code),
        "Professor": notion_props.rich_text(ex_course.professor) if ex_course.professor else None,
        "Semester": notion_props.relation([semester_notion_id]) if semester_notion_id else None,
        "Syllabus": notion_props.url(ex_course.syllabus_html) if ex_course.syllabus_html else None,
    }

    return {k: v for k, v in properties.items() if v is not None}
    
    


# --- Main ---
def sync_courses(external: ExternalClient, notion: NotionClient, term: Optional[str] = None, sync_assignments: bool = True) -> list[dict]:
    """Discover Courses from external connection and upsert into notion

    Args:
        external (ExternalClient): _description_
        notion (NotionClient): _description_
        term (Optional[str]): _description_

    Returns:
        list[dict]: A list of dictionaries with the output from being upserted into notion. \nStructure: {"page": properties dict of existing or created page, "was_created": boolean}
    """
    
    ex_courses = external.get_active_courses()

    results = []
    for course in ex_courses:
        term_name = term or course.term_name
        semester_page = notion.get_page_by_title(settings.notion_semesters_ds_id, "Term", term_name) if term_name else None
        semester_notion_id = semester_page["id"] if semester_page else None

        result = notion.upsert_by_source(
            ds_id=settings.notion_courses_ds_id,
            source=external.source_name,
            external_id=course.id,
            properties=_external_course_to_notion_props(course, semester_notion_id),
        )
        results.append(result)
        
        # Sync assignments for course
        if sync_assignments:
            sync_assignments_for_course(external, notion, course.id, semester_notion_id)
            
    return results


if __name__ == "__main__":
    from src.clients.canvas import CanvasClient
    
    canvas = CanvasClient()
    notion = NotionClient()
    results = sync_courses(canvas, notion)
    from pprint import pprint
    for r in results:
        print(f"  {'+' if r['was_created'] else '·'} {notion_props.read_title(r['page']['properties'], 'Course Name')}")
        #pprint(r['page']['properties'])