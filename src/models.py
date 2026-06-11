from dataclasses import dataclass

from src.clients.sis_client import SISClient
from src.clients.notion import NotionClient
from src.template.config import TemplateSettings


@dataclass
class SyncContext:
    external: SISClient
    notion: NotionClient
    workspace: TemplateSettings
