from langchain_community.tools.tavily_search import TavilySearchResults

from tools.notion.clipboard.notion_clipboard_tool import NotionClipboardTool


def get_research_tools():
    search_tool = TavilySearchResults(max_results=2)
    clipboard_tool = NotionClipboardTool()
    return [search_tool, clipboard_tool]