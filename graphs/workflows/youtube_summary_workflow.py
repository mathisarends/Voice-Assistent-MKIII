import asyncio
from typing import Optional, Dict, Any, List

from langchain_anthropic import ChatAnthropic
from config.settings import DEFAULT_LLM_MODEL
from graphs.base_graph import BaseGraph
from langgraph.graph import StateGraph, END
from states.state_definitions import State
from tools.notion.clipboard.notion_clipboard_manager import NotionClipboardManager
from langgraph.checkpoint.memory import MemorySaver
from tools.youtube.youtbe_video_summarizer import YoutubeVideoSummarizer
from tools.youtube.youtube_finder import YoutubeFinder
from tools.youtube.youtube_transcript import YoutubeTranscript


class YoutubeSummaryState(State):
    """Zustand für den YouTube-Summary-Workflow."""
    video_url: Optional[str] = None
    video_title: Optional[str] = None
    search_query: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None


class YoutubeSummaryWorkflow(BaseGraph):
    """Ein Workflow für die Zusammenfassung eines YouTube-Videos basierend auf einer Beschreibung."""
    
    SEARCH_QUERY_PROMPT = """
    Du bist ein Experte für YouTube-Suchen. Extrahiere aus der folgenden Anfrage den YouTuber-Namen und das Videothema.
    Formuliere einen präzisen Suchbegriff für YouTube im Format "youtubername thema".
    
    Anfrage: {user_message}
    
    Suchbegriff:
    """
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or DEFAULT_LLM_MODEL
        self.llm = ChatAnthropic(model=self.model_name)
        
        # Initialisierung der Tools
        self._init_tools()
        
        # Graph-Setup
        self.graph_builder = StateGraph(YoutubeSummaryState)
        self.memory = MemorySaver()
    
    def _init_tools(self):
        """Initialisiert die benötigten Tools für den Workflow."""
        self.youtube_finder = YoutubeFinder()
        self.youtube_transcript = YoutubeTranscript()
        self.youtube_video_summarizer = YoutubeVideoSummarizer()
        self.notion_clipboard_manager = NotionClipboardManager()
    
    def _extract_user_message(self, messages):
        """Extrahiert die letzte Benutzernachricht aus den Nachrichten."""
        for message in messages:
            if hasattr(message, "type") and message.type == "human":
                return message.content
            elif isinstance(message, dict) and message.get("role") == "user":
                return message.get("content", "")
        return ""
        
    def _optimize_search_query_from_prompt(self, state: YoutubeSummaryState) -> Dict[str, Any]:
        """Optimiert die Suchanfrage basierend auf der Benutzereingabe."""
        messages = state.get("messages", [])
        last_user_message = self._extract_user_message(messages)
        
        search_query = self.llm.invoke([
            {"role": "user", "content": self.SEARCH_QUERY_PROMPT.format(user_message=last_user_message)}
        ]).content.strip()
        
        return {
            "search_query": search_query, 
            "messages": [{"role": "assistant", "content": f"Suche nach YouTube-Videos mit dem Suchbegriff: {search_query}"}]
        }
    
    async def _find_video(self, search_query: str) -> Dict[str, str]:
        """Findet ein YouTube-Video basierend auf der Suchanfrage."""
        return await self.youtube_finder.find_youtube_video(search_query)
    
    def _find_video_url_and_title_by_prompt(self, state: YoutubeSummaryState) -> Dict[str, Any]:
        """Findet ein YouTube-Video basierend auf der optimierten Suchanfrage."""
        search_query = state.get("search_query", "")
        
        result = asyncio.run(self._find_video(search_query))
        
        return {
            "video_url": result.get("url"),
            "video_title": result.get("title"),
            "messages": [{"role": "assistant", "content": f"Ich habe ein passendes Video gefunden: '{result.get('title')}'"}]
        }
                
    def _get_transcript_for_youtube_video_by_transcript(self, state: YoutubeSummaryState) -> Dict[str, Any]:
        """Ruft das Transkript für das identifizierte YouTube-Video ab."""
        video_url = state.get("video_url")
        video_title = state.get("video_title", "")
        
        if not video_url:
            return {
                "messages": [{"role": "assistant", "content": "Ich konnte kein passendes YouTube-Video finden. Bitte versuche es mit einer spezifischeren Anfrage."}]
            }
        
        transcript_result = self.youtube_transcript.get_transcript_by_url(video_url)
        
        return {
            "transcript": transcript_result,
            "messages": [{"role": "assistant", "content": f"Ich habe das Transkript für '{video_title}' erfolgreich abgerufen und bereite nun die Zusammenfassung vor."}]
        }
    
    async def _create_summary(self, transcript: str, video_title: str) -> str:
        """Erstellt eine Zusammenfassung des Transkripts."""
        return await self.youtube_video_summarizer.create_summary(transcript, video_title)
    
    def _get_summary_for_youtube_video_by_transcript(self, state: YoutubeSummaryState) -> Dict[str, Any]:
        """Erstellt eine Zusammenfassung des Video-Transkripts."""
        transcript = state.get("transcript", "")
        video_title = state.get("video_title", "")
        
        if isinstance(transcript, str) and "Fehler" in transcript:
            return {
                "summary": "Zusammenfassung nicht möglich: Kein Transkript verfügbar",
                "messages": [{"role": "assistant", "content": f"Leider konnte ich keine Zusammenfassung erstellen, da kein Transkript für '{video_title}' verfügbar ist."}]
            }
        
        summary = asyncio.run(self._create_summary(transcript, video_title))

        return {
            "summary": summary,
            "messages": [{"role": "assistant", "content": f"Ich habe eine Zusammenfassung des Videos '{video_title}' erstellt und bereite sie für die Zwischenablage vor."}]
        }
    
    def _format_clipboard_content(self, video_title: str, video_url: str, summary: str) -> str:
        """Formatiert den Inhalt für die Zwischenablage."""
        return f"""
        # Zusammenfassung: {video_title}
        Video-Link: {video_url}
        
        ## Zusammenfassung
        
        {summary}
        """
    
    def _save_summary_to_clipboard(self, state: YoutubeSummaryState) -> Dict[str, Any]:
        """Speichert die Zusammenfassung in der Zwischenablage für Notion."""
        summary = state.get("summary", "")
        video_title = state.get("video_title", "")
        video_url = state.get("video_url", "")
        
        if not summary or summary == "Zusammenfassung nicht möglich: Kein Transkript verfügbar":
            return {
                "messages": [{"role": "assistant", "content": f"Ich konnte keine Zusammenfassung für '{video_title}' in die Zwischenablage kopieren, da keine Zusammenfassung erstellt werden konnte."}]
            }
        
        content = self._format_clipboard_content(video_title, video_url, summary)
        
        asyncio.run(self.notion_clipboard_manager.append_to_clipboard(content))
        
        return {
            "messages": [{"role": "assistant", "content": f"✅ Fertig! Ich habe eine Zusammenfassung des Videos '{video_title}' erstellt und in die Zwischenablage kopiert. Du kannst sie jetzt in Notion einsehen."}]
        }
        
    def build_graph(self):
        """
        Baut den Graphen für den YouTube-Summary-Workflow.
        """
        # Knoten zum Graphen hinzufügen
        self.graph_builder.add_node("start_node", lambda state: state)
        self.graph_builder.add_node("optimize_search_query", self._optimize_search_query_from_prompt)
        self.graph_builder.add_node("find_video", self._find_video_url_and_title_by_prompt)
        self.graph_builder.add_node("get_transcript", self._get_transcript_for_youtube_video_by_transcript)
        self.graph_builder.add_node("create_summary", self._get_summary_for_youtube_video_by_transcript)
        self.graph_builder.add_node("save_to_clipboard", self._save_summary_to_clipboard)
        
        # Den YouTube-Workflow-Pfad definieren
        self._add_workflow_edges()
        
        self.graph_builder.set_entry_point("start_node")
        
        return self.graph_builder.compile(checkpointer=self.memory)
    
    def _add_workflow_edges(self):
        """Fügt die Kanten zum Graphen hinzu."""
        self.graph_builder.add_edge("start_node", "optimize_search_query")
        self.graph_builder.add_edge("optimize_search_query", "find_video")
        self.graph_builder.add_edge("find_video", "get_transcript")
        self.graph_builder.add_edge("get_transcript", "create_summary")
        self.graph_builder.add_edge("create_summary", "save_to_clipboard")
        self.graph_builder.add_edge("save_to_clipboard", END)
    
if __name__ == "__main__":
    workflow = YoutubeSummaryWorkflow()
    results = workflow.run("Ich möchte das Youtube Video von Ali Abdaal zu dem Thema 'Why you feel behind in live' zusammenfassen lassen.")
    for result in results:
        print(result["messages"][-1]["content"])