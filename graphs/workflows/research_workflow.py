from typing import Optional

from langchain_community.tools.tavily_search import TavilySearchResults

from graphs.core.base_graph import BaseGraph
from tools.notion.clipboard.notion_clipboard_tool import NotionClipboardTool


class ResearchWorkflow(BaseGraph):
    """Ein Workflow für Recherche und Dokumentation."""

    def __init__(self, model_name: Optional[str] = None):
        search_tool = TavilySearchResults(max_results=2)
        clipboard_tool = NotionClipboardTool()
        tools = [search_tool, clipboard_tool]

        super().__init__(tools, model_name)
