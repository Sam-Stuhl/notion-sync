from notion_client import Client, collect_paginated_api
from typing import Optional

from src.config import settings
from src.clients.notion_props import read_rich_text, rich_text, select, title


class NotionClient:
    def __init__(self, token: Optional[str] = None):
        if token is None:
            token = settings.notion_access_token
        self._client = Client(auth=token)
        
    def query_data_source(self, ds_id: str, filter_dict: Optional[dict] = None, sorts_dict: Optional[dict] = None) -> list:
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
    
    def update_view(self, view_id: str, filter_dict: dict, sorts_dict: Optional[dict] = None) -> dict:
        """Updates a views filters and sorts

        Returns:
            dict: Simple dict containing mainly the id of the updated view with its parent 
        """
        kwargs = {}
        if sorts_dict:
            kwargs["sorts"] = sorts_dict
        
        return self._client.views.update(view_id=view_id, filter=filter_dict, **kwargs)

    def get_page(self, page_id: str) -> dict:
        """Get page as dict

        Returns:
            dict: Page described as dict
        """
        
        return self._client.pages.retrieve(page_id=page_id)
    
    def get_page_by_title(self, ds_id: str, title_prop: str, title_value: str) -> dict | None:
        """Look up a single page by a title property value.

        Returns:
            dict: The page, or None if not found.
        """
        pages = self._client.data_sources.query(ds_id, filter={
            "property": title_prop,
            "title": {"equals": title_value},
        })["results"]
        return pages[0] if pages else None

    def get_pages_by_source(self, ds_id: str, source: str) -> dict[str, dict]:
        """Bulk-fetch all pages for a given source. Returns {external_id: page}."""
        pages = collect_paginated_api(
            self._client.data_sources.query,
            data_source_id=ds_id,
            filter={"property": "Source", "select": {"equals": source}},
        )
        result: dict[str, dict] = {}
        for page in pages:
            props = page.get("properties", {})
            try:
                ext_id = read_rich_text(props, "External ID")
                if ext_id:
                    result[ext_id] = page
            except (KeyError, TypeError):
                pass
        return result

    def create_sourced_page(
        self, ds_id: str, source: str, external_id: str, properties: dict
    ) -> dict:
        """Create a page with Source + External ID automatically included."""
        return self.create_page(ds_id, {
            **properties,
            "Source": select(source),
            "External ID": rich_text(external_id),
        })

    def update_sourced_page(
        self, page_id: str, source: str, external_id: str, properties: dict
    ) -> dict:
        """Update a page with Source + External ID automatically included."""
        return self.update_page(page_id, {
            **properties,
            "Source": select(source),
            "External ID": rich_text(external_id),
        })

    def get_page_by_source(self, ds_id: str, source: str, external_id: str) -> dict | None:
        """Look up a single page by (Source, External ID) composite key.

        Returns:
            dict: The page, or None if not found.
        """
        pages = self._client.data_sources.query(ds_id, filter={
            "and": [
                {"property": "Source", "select": {"equals": source}},
                {"property": "External ID", "rich_text": {"equals": external_id}},
            ]
        })["results"]
        return pages[0] if pages else None

    def upsert_by_source(
        self,
        ds_id: str,
        source: str,
        external_id: str,
        properties: dict,
        create_only_props: dict | None = None,
        stored_hash: str | None = None,
        new_hash: str | None = None,
    ) -> dict | None:
        """Upsert a Notion page by (Source, External ID) composite key.

        Returns None if the page exists and stored_hash == new_hash (nothing to write).
        Returns {"page": ..., "was_created": bool} otherwise.
        """
        _filter = {
            "and": [
                {"property": "Source", "select": {"equals": source}},
                {"property": "External ID", "rich_text": {"equals": external_id}},
            ]
        }
        _properties = {
            **properties,
            "Source": select(source),
            "External ID": rich_text(external_id),
        }

        pages = self._client.data_sources.query(ds_id, filter=_filter)["results"]

        if len(pages) > 1:
            raise RuntimeError(
                f"Composite key collision in {ds_id}: "
                f"found {len(pages)} pages matching Source={source!r}, External ID={external_id!r}"
            )
        elif not pages:
            page = self.create_page(ds_id, {**_properties, **(create_only_props or {})})
            return {"page": page, "was_created": True}
        else:
            if stored_hash is not None and stored_hash == new_hash:
                return None  # page exists and unchanged
            page = self.update_page(pages[0]["id"], _properties)
            return {"page": page, "was_created": False}
            
        
            
            
        
        

if __name__ == "__main__":
    notion = NotionClient()
    
    
    from pprint import pprint
    
    
    #pprint(notion.query_data_source(settings.notion_tasks_ds_id))
    #pprint(notion.query_data_source(settings.notion_courses_ds_id))
    pprint(notion.query_data_source(settings.notion_semesters_ds_id))
    
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