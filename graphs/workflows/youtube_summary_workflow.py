from typing import Optional, Dict, Any
from langgraph.graph import StateGraph
from langchain_core.messages import AIMessage, HumanMessage
from graphs.base_graph import BaseGraph
from tools.youtube.youtube_finder_tool import YoutubeFinderTool
from tools.youtube.youtube_transcript_tool import YoutubeTranscriptTool
from tools.notion.clipboard.notion_clipboard_tool import NotionClipboardTool
from langchain_core.tools import tool

#TODO: Implement this bitch.

class YoutubeSummaryWorkflow(BaseGraph):
    """Ein Workflow für die Zusammenfassung eines YouTube-Videos basierend auf einer Beschreibung."""
    
    def __init__(self, model_name: Optional[str] = None):
        # Tools initialisieren
        self.youtube_finder = YoutubeFinderTool()
        self.youtube_transcript = YoutubeTranscriptTool()
        self.notion_clipboard = NotionClipboardTool()
        
        # Tools als Liste für BaseGraph
        tools = [self.youtube_finder, self.youtube_transcript, self.notion_clipboard]
        super().__init__(tools, model_name)