from typing import Optional

from tools.notion.clipboard.notion_clipboard_tool import NotionClipboardTool
from workflow.core.base_graph import BaseGraph


class DocumentWorkflow(BaseGraph):
    """Ein Workflow für reine Dokumentation ohne Recherche."""

    def __init__(self, model_name: Optional[str] = None):
        clipboard_tool = NotionClipboardTool()
        tools = [clipboard_tool]

        super().__init__(tools, model_name)
