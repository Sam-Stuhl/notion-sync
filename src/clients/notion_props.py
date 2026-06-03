"""
Formatters for Notion page property values.

Notion's API requires every property write to be wrapped in a type-discriminated
dict matching the property's type. These helpers wrap bare Python values in the
correct shapes so callers can write `notion_props.title("Hello")` instead of
`{"title": [{"text": {"content": "Hello"}}]}` everywhere.

Each function returns the dict that goes as the *value* for a property name
inside a `properties` dict. Example:

    properties = {
        "Task Name": notion_props.title("Read chapter 4"),
        "Date": notion_props.date("2026-09-01"),
        "Done": notion_props.checkbox(False),
    }
"""
from datetime import date as date_type, datetime
from typing import Optional, Union


# ---------- Text-like properties ----------

def title(text: str) -> dict:
    """The page title. Every database has exactly one title property."""
    return {"title": [{"type": "text", "text": {"content": text}}]}


def rich_text(text: str) -> dict:
    """A plain text property (no formatting)."""
    return {"rich_text": [{"type": "text", "text": {"content": text}}]}


# ---------- Scalar properties ----------

def number(n: Optional[Union[int, float]]) -> dict:
    """A number property. Pass None to clear."""
    return {"number": n}


def checkbox(value: bool) -> dict:
    """A checkbox property."""
    return {"checkbox": value}


def url(href: Optional[str]) -> dict:
    """A URL property. Pass None to clear."""
    return {"url": href}


def email(address: Optional[str]) -> dict:
    """An email property. Pass None to clear."""
    return {"email": address}


def phone_number(number: Optional[str]) -> dict:
    """A phone number property. Pass None to clear."""
    return {"phone_number": number}


# ---------- Select properties ----------

def select(name: Optional[str]) -> dict:
    """A single-select property. Pass the option name as a string, or None to clear."""
    return {"select": {"name": name} if name else None}


def multi_select(names: list[str]) -> dict:
    """A multi-select property. Pass a list of option names."""
    return {"multi_select": [{"name": n} for n in names]}


def status(name: Optional[str]) -> dict:
    """A status property (similar to select but with a different type in Notion)."""
    return {"status": {"name": name} if name else None}


# ---------- Date property ----------

def date(
    start: Optional[Union[str, date_type, datetime]],
    end: Optional[Union[str, date_type, datetime]] = None,
) -> dict:
    """
    A date property. Accepts ISO strings, date, or datetime objects.

    Pass `end` to make it a date range. Pass `start=None` to clear.
    """
    if start is None:
        return {"date": None}

    payload = {"start": _to_iso(start)}
    if end is not None:
        payload["end"] = _to_iso(end)
    return {"date": payload}


def _to_iso(value: Union[str, date_type, datetime]) -> str:
    """Internal: convert dates/datetimes to ISO format strings."""
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date_type):
        return value.isoformat()
    raise TypeError(f"Unsupported date type: {type(value)}")


# ---------- Relation property ----------

def relation(page_ids: list[str]) -> dict:
    """A relation property. Pass a list of related page IDs (UUIDs as strings)."""
    return {"relation": [{"id": pid} for pid in page_ids]}


# ---------- People property ----------

def people(user_ids: list[str]) -> dict:
    """A people property. Pass a list of Notion user IDs."""
    return {"people": [{"id": uid} for uid in user_ids]}


# ---------- Files property ----------

def files(items: list[tuple[str, str]]) -> dict:
    """
    A files & media property. Pass a list of (name, url) tuples for external files.

    Notion's API only supports referencing external URLs — not uploading files directly.
    """
    return {
        "files": [
            {"name": name, "type": "external", "external": {"url": url}}
            for name, url in items
        ]
    }