import asyncio
from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

from tools.notion.clipboard.notion_clipboard_manager import NotionClipboardManager

class NotionClipboardInput(BaseModel):
    """Eingabemodell für das Notion Clipboard Tool."""
    content: str

class NotionClipboardTool(BaseTool):
    """Speichert formatierten Text mit Markdown-Unterstützung in die Notion-Zwischenablage."""
    
    name: str = "notion_clipboard"
    description: str = "Speichert formatierten Text in die Notion-Zwischenablage mit Markdown-Unterstützung."
    args_schema: Type[BaseModel] = NotionClipboardInput

    # `exclude=True` sorgt dafür, dass Pydantic dieses Feld ignoriert
    clipboard_manager: NotionClipboardManager = Field(default_factory=NotionClipboardManager, exclude=True)
    
    def _run(self, content: str) -> str:
        return asyncio.run(self._arun(content))

    async def _arun(self, content: str) -> str:
        try:
            result = await self.clipboard_manager.append_to_clipboard(content)
            return f"Inhalt erfolgreich gespeichert: {result}"
        except Exception as e:
            return f"Fehler beim Speichern in die Notion-Zwischenablage: {str(e)}"