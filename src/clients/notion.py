from notion_client import Client, collect_paginated_api

from src.config import settings
from src.clients.notion_props import rich_text, select, title

class NotionClient:
    def __init__(self):
        self._client = Client(auth=settings.notion_access_token)
        
    def query_data_source(self, ds_id: str, filter_dict: dict = None, sorts_dict: list = None) -> list:
        """Get pages in data source

        Returns:
            list: List of pages in dictionary format
        """
        
        kwargs = {}
        if filter_dict:
            kwargs["filter"] = filter_dict
        if sorts_dict:
            kwargs["sorts"] = sorts_dict
        query = collect_paginated_api(self._client.data_sources.query, data_source_id=ds_id, **kwargs)
        
        return query
    
    def create_page(self, parent_ds_id: str, properties: dict) -> str:
        """Creates a page in specified data source

        Returns:
            dict: Created page represented as a dictionary
        """
        
        page = self._client.pages.create(parent={"data_source_id": parent_ds_id}, properties=properties)
        
        return page
    
    def update_page(self, page_id: str, properties: dict) -> str:
        """Update properties of a pre-existing page

        Returns:
            dict: Updated page represented as a dictionary
        """
        
        page = self._client.pages.update(page_id=page_id, properties=properties)
        
        return page
    
    def get_page(self, page_id: str) -> dict:
        """Get page as dict

        Returns:
            dict: Page described as dict
        """
        
        return self._client.pages.retrieve(page_id=page_id)
    
    def upsert_by_source(self, ds_id: str, source: str, external_id: str, properties: dict) -> dict:
        """Upsert a Notion page by (Source, External ID) composite key — update if it exists, create if it doesn't. Raises if multiple matches found.

        Returns:
            dict: Dictionary containing the upserted page with key "page" and a "was_created" flag
            indicating whether the page was newly created (True) or updated (False).
        """
        was_created = False
        
        _filter = {
            "and": [
                {
                    "property": "Source",
                    "select": {"equals": source}
                },
                {
                    "property": "External ID",
                    "rich_text": {"equals": external_id}
                }
            ]
        }
        
        _properties = {
            **properties,
            "Source": select(source),
            "External ID": rich_text(external_id)
        }
        
        pages = self._client.data_sources.query(ds_id, filter=_filter)["results"]
        
        upserted_page = {}
            
          
        if len(pages) > 1: # Raise Exception if multiple pages match
            raise RuntimeError(
                f"Composite key collision in {ds_id}: "
                f"found {len(pages)} pages matching Source={source!r}, External ID={external_id!r}"
            )  
        elif not pages: # Insert new page if none exist
            upserted_page = self.create_page(ds_id, _properties)
            was_created = True
        else: # Update pages if they exist
            upserted_page = self.update_page(pages[0]["id"], _properties)
            
            
        return {
            "page": upserted_page,
            "was_created": was_created
        }
            
        
            
            
        
        

if __name__ == "__main__":
    notion = NotionClient()
    
    
    from pprint import pprint
    
    
    #pprint(notion.query_data_source(settings.notion_tasks_ds_id))
    pprint(notion.query_data_source(settings.notion_courses_ds_id))
    
    properties = {'Application': {'has_more': False,
                                 'id': 'HsAm',
                                 'relation': [],
                                 'type': 'relation'},
                 'Area': {'id': 'UHB%7C', 'select': None, 'type': 'select'},
                 'Club': {'has_more': False,
                          'id': 'M%3EgS',
                          'relation': [],
                          'type': 'relation'},
                 'Course': {'has_more': False,
                            'id': 'AF~y',
                            'relation': [],
                            'type': 'relation'},
                 'Date': {'date': {'end': None,
                                   'start': '2026-06-04',
                                   'time_zone': None},
                          'id': '%3BemV',
                          'type': 'date'},
                 'Done': {'checkbox': False,
                          'id': 'x%5D%5BX',
                          'type': 'checkbox'},
                 'External ID': {'id': 'iFa%3D',
                                 'rich_text': [{'annotations': {'bold': False,
                                                                'code': False,
                                                                'color': 'default',
                                                                'italic': False,
                                                                'strikethrough': False,
                                                                'underline': False},
                                                'href': None,
                                                'plain_text': '1',
                                                'text': {'content': '1',
                                                         'link': None},
                                                'type': 'text'}],
                                 'type': 'rich_text'},
                 'Kind': {'id': 'OQ%60W', 'select': None, 'type': 'select'},
                 'Project': {'has_more': False,
                             'id': '%3EF%7Cl',
                             'relation': [],
                             'type': 'relation'},
                 'Source': {'id': 'O%3AgM',
                            'select': {'color': 'green',
                                       'id': 'q}bU',
                                       'name': 'Canvas'},
                            'type': 'select'},
                 'Task Name': {'id': 'title',
                               'title': [{'annotations': {'bold': False,
                                                          'code': False,
                                                          'color': 'default',
                                                          'italic': False,
                                                          'strikethrough': False,
                                                          'underline': False},
                                          'href': None,
                                          'plain_text': 'test 9',
                                          'text': {'content': 'test 9',
                                                   'link': None},
                                          'type': 'text'}],
                               'type': 'title'},
                 'Term': {'id': '%3CRZS', 'select': None, 'type': 'select'}}
    
    #print(notion.create_page(settings.notion_tasks_ds_id, properties))
    #print(notion.update_page("3734330f-6a04-8168-852c-ffd42d3c3aee", properties))
    #pprint(notion.get_page("3734330f-6a04-8168-852c-ffd42d3c3aee"))
    
    #pprint(notion.upsert_by_property(settings.notion_tasks_ds_id, "Canvas", "3", properties))