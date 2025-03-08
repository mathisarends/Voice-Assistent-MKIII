from tools.base import BaseTool
from config.settings import TAVILY_MAX_RESULTS
from langchain_community.tools.tavily_search import TavilySearchResults


class TavilySearchTool(BaseTool):
    """Tool für die Tavily-Websuche."""
    
    def __init__(self, max_results=None):
        self.name = "tavily_search"
        self.description = "Suche im Internet nach aktuellen Informationen zu einem Thema."
        self.max_results = max_results or TAVILY_MAX_RESULTS
        self._tavily_tool = TavilySearchResults(max_results=self.max_results)
    
    def _run(self, query: str) -> str:
        """Führt die Tavily-Suche durch."""
        return self._tavily_tool.invoke(query)
