from typing import Optional

from src.clients import notion_props
from src.clients.notion import NotionClient
from src.clients.external_client import ExternalClient, ExternalCourse
from src.config import settings

# --- Helpers ---

def _external_course_to_notion_props(ex_c: ExternalCourse, term: Optional[str]) -> dict:
    """Takes in external course and converts it to a dictionary with the properties of a notion course

    Returns:
        dict: Notion Course properties dict
    """
    properties = {
        "Course Name": notion_props.title(ex_c.name),
        "Code": notion_props.rich_text(ex_c.code),
        "Professor": notion_props.rich_text(ex_c.professor) if ex_c.professor else None,
        "Term": notion_props.select(term or ex_c.term_name),
        "Syllabus": notion_props.url(ex_c.syllabus_html) if ex_c.syllabus_html else None,
    }

    return {k: v for k, v in properties.items() if v is not None}
    
    


# --- Main ---
def discover_courses(external: ExternalClient, notion: NotionClient, term: Optional[str] = None) -> list[dict]:
    """Discover Courses from external connection and upsert into notion

    Args:
        external (ExternalClient): _description_
        notion (NotionClient): _description_
        term (Optional[str]): _description_

    Returns:
        list[dict]: A list of dictionaries with the output from being upserted into notion. \nStructure: {"page": properties dict of existing or created page, "was_created": boolean}
    """
    
    # Get external courses
    ex_courses = external.get_active_courses()
    
    # Upsert courses to notion
    results = []
    for course in ex_courses:
        result = notion.upsert_by_source(
            ds_id=settings.notion_courses_ds_id,
            source=external.source_name,
            external_id=course.id,
            properties=_external_course_to_notion_props(course, term),
        )
        results.append(result)
    return results


if __name__ == "__main__":
    from src.clients.canvas import CanvasClient
    
    canvas = CanvasClient()
    notion = NotionClient()
    results = discover_courses(canvas, notion)
    from pprint import pprint
    for r in results:
        print(f"  {'+' if r['was_created'] else '·'} {notion_props.read_title(r['page']['properties'], 'Course Name')}")
        #pprint(r['page']['properties'])