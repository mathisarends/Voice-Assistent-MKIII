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
    """Erweiterter Zustand für den YouTube-Summary-Workflow."""
    video_id: Optional[str]
    video_title: Optional[str]
    search_query: Optional[str]
    transcript: Optional[str]
    summary: Optional[str]


class YoutubeSummaryWorkflow(BaseGraph):
    """Ein Workflow für die Zusammenfassung eines YouTube-Videos basierend auf einer Beschreibung."""
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or DEFAULT_LLM_MODEL
        self.llm = ChatAnthropic(model=self.model_name)
        
        self.youtube_finder = YoutubeFinder()
        self.youtube_transcript = YoutubeTranscript()
        self.youtube_video_summarizer = YoutubeVideoSummarizer()
        self.notion_clipboard_manager = NotionClipboardManager()
        
        self.graph_builder = StateGraph(YoutubeSummaryState)
        self.memory = MemorySaver()
        
    def _optimize_search_query_from_prompt(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Optimiert die Suchanfrage basierend auf der Benutzereingabe."""
        # Extrahiere den letzten Benutzertext
        messages = state.get("messages", [])
        
        # LangChain Messages verwenden ein anderes Format
        last_user_message = ""
        for message in messages:
            # Prüfen ob es ein LangChain Message-Objekt ist
            if hasattr(message, "type") and message.type == "human":
                last_user_message = message.content
                break
            # Oder ein Dictionary mit role
            elif isinstance(message, dict) and message.get("role") == "user":
                last_user_message = message.get("content", "")
                break
        
        print("last_user_message", last_user_message)
        
        # Da wir hier kein self.llm haben:
        # Als Notlösung nehmen wir einfach den ursprünglichen Query
        search_query = last_user_message
        
        return {"search_query": search_query}
    
    def _find_video_url_and_title_by_prompt(self, state: YoutubeSummaryState) -> YoutubeSummaryState:
        search_query = state.get("search_query", "")
        
        result = asyncio.run(self.youtube_finder.find_youtube_video(search_query))
        
        return {
            "video_id": result.get("url"),
            "video_title": result.get("title")
        }
                
    def _get_transcript_for_youtube_video_by_transcript(self, state: YoutubeSummaryState) -> YoutubeSummaryState:
        """Ruft das Transkript für das identifizierte YouTube-Video ab."""
        video_id = state.get("video_id")
        if not video_id:
            # Fehlerfall: Kein Video gefunden
            message = self.llm.invoke([
                {"role": "user", "content": "Ich konnte kein passendes YouTube-Video finden. Bitte versuche es mit einer spezifischeren Anfrage."}
            ])
            return {"messages": [message]}
        
        transcript_result = self.youtube_transcript.get_transcript_by_url(video_id)
        return {"transcript": transcript_result}
    
    def _get_summary_for_youtube_video_by_transcript(self, state: YoutubeSummaryState) -> YoutubeSummaryState:
        """Erstellt eine Zusammenfassung des Video-Transkripts."""
        transcript = state.get("transcript", "")
        video_title = state.get("video_title", "")
        
        summary = asyncio.run(self.youtube_video_summarizer.create_summary(transcript, video_title))

        return {
            "summary": summary
        }
    
    def _save_summary_to_clipboard(self, state: YoutubeSummaryState) -> YoutubeSummaryState:
        """Speichert die Zusammenfassung in der Zwischenablage für Notion."""
        summary = state.get("summary", "")
        video_title = state.get("video_title", "")
        video_id = state.get("video_id", "")
        
        content = f"""
        # Zusammenfassung: {video_title}
        
        Video-Link: https://www.youtube.com/watch?v={video_id}
        
        ## Zusammenfassung
        
        {summary}
        """
        
        asyncio.run(self.notion_clipboard_manager.append_to_clipboard(content))
        
        return {
            "messages": [
                {
                    "role": "assistant", 
                    "content": f"Ich habe eine Zusammenfassung des Videos '{video_title}' erstellt und in die Zwischenablage kopiert. Du kannst sie jetzt in Notion einfügen."
                }
            ]
        }
    
    def build_graph(self):
        """
        Baut den Graphen für den YouTube-Summary-Workflow.
        """
        # Standardknoten für den Chatbot
        def _start_node(state: YoutubeSummaryState) -> YoutubeSummaryState:
            """Einfacher Startknoten, der den Zustand unverändert weitergibt."""
            return state
        
        # Knoten zum Graphen hinzufügen
        self.graph_builder.add_node("start_node", _start_node)
        self.graph_builder.add_node("optimize_search_query", self._optimize_search_query_from_prompt)
        self.graph_builder.add_node("find_video", self._find_video_url_and_title_by_prompt)
        self.graph_builder.add_node("get_transcript", self._get_transcript_for_youtube_video_by_transcript)
        self.graph_builder.add_node("create_summary", self._get_summary_for_youtube_video_by_transcript)
        self.graph_builder.add_node("save_to_clipboard", self._save_summary_to_clipboard)
        
        # Den YouTube-Workflow-Pfad definieren
        self.graph_builder.add_edge("start_node", "optimize_search_query")
        self.graph_builder.add_edge("optimize_search_query", "find_video")
        self.graph_builder.add_edge("find_video", "get_transcript")
        self.graph_builder.add_edge("get_transcript", "create_summary")
        self.graph_builder.add_edge("create_summary", "save_to_clipboard")
        self.graph_builder.add_edge("save_to_clipboard", END)
        
        self.graph_builder.set_entry_point("start_node")
        
        return self.graph_builder.compile(checkpointer=self.memory)
    
if __name__ == "__main__":
    workflow = YoutubeSummaryWorkflow()
    results = workflow.run("Ich möchte das Youtube Video von Ali Abdaal zu einer persönlichen Webseite zusammenfassen.")
    for result in results:
        print(result["messages"][-1].content)