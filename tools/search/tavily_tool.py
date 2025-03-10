from tools.base import BaseTool
from config.settings import TAVILY_MAX_RESULTS
from langchain_community.tools.tavily_search import TavilySearchResults

class TavilySearchTool(BaseTool):
    """Tool für die Tavily-Websuche mit zusätzlichen Optionen für Quellenpräferenzen."""
    
    def __init__(self, max_results=None, include_domains=None, exclude_domains=None, search_depth="basic"):
        """
        Initialisiert das Tavily-Suchtool mit erweiterten Optionen.
        
        Args:
            max_results: Maximale Anzahl an Ergebnissen (Standard aus TAVILY_MAX_RESULTS)
            include_domains: Liste von Domains, die bevorzugt werden sollen (z.B. ["github.com"])
            exclude_domains: Liste von Domains, die ausgeschlossen werden sollen
            search_depth: Suchtiefe ("basic" oder "advanced")
        """
        self.name = "tavily_search"
        self.description = "Suche im Internet nach aktuellen Informationen zu einem Thema."
        self.max_results = max_results or TAVILY_MAX_RESULTS
        
        tavily_params = {
            "max_results": self.max_results,
            "search_depth": search_depth
        }
        
        if include_domains:
            tavily_params["include_domains"] = include_domains
            
        if exclude_domains:
            tavily_params["exclude_domains"] = exclude_domains
            
        self._tavily_tool = TavilySearchResults(**tavily_params)
    
    def _run(self, query: str) -> str:
        return self._tavily_tool.invoke(query)