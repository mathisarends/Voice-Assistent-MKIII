import textwrap
from typing import Any, ClassVar, Dict, List, Optional

from langchain.schema import AIMessage
from langchain.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from config.settings import DEFAULT_LLM_MODEL
from graphs.core.state_definitions import State
from service.speech_service import SpeechService
from util.loggin_mixin import LoggingMixin


class BaseGraph(LoggingMixin):
    """Basisklasse für alle Graph-Workflows in der Anwendung."""

    # Basis-Systemprompt als Klassenvariable
    BASE_SYSTEM_PROMPT: ClassVar[str] = textwrap.dedent(
        """
    Du bist ein KI-Assistent der für einen Voice-Agenten-Workflow entwickelt wurde.
    WICHTIGE ANWEISUNGEN FÜR STATUSUPDATES:
    - Gib nur kurze, sachliche Statusupdates über deine aktuellen Aktionen aus
    - KEIN Präfix wie "Aktion:" verwenden
    - Nur neue, substantielle Informationen mitteilen
    - Bei keinen neuen Informationen: NICHTS ausgeben
    - Halte Updates extrem knapp (max. 5-7 Wörter)
    - Beispiele für gute Updates:
    * "Suche verfügbare Lichtszenen"
    * "3 passende Szenen gefunden"
    * "Aktiviere 'Verträumter Sonnenuntergang'"
    * "Lichtszene erfolgreich aktiviert"

    ANWEISUNGEN FÜR FINALE ANTWORTEN (SPRACHOPTIMIERT):
    - Deine Antworten werden LAUT VORGELESEN, optimiere sie für Sprachausgabe
    - Vermeide Symbole, Sonderzeichen und Emojis (werden nicht richtig ausgesprochen)
    - Verwende einfache Satzstrukturen und klare Aussprache
    - Beginne mit einer kurzen Bestätigung der Aktion (1-2 Sätze)
    - Für Lichtszenen: "Die Lichtszene X ist jetzt aktiv."
    - Für Musikwiedergabe: "Ich spiele jetzt X ab."
    - Für Informationen: "Hier sind die Informationen zu X:"
    - Keine unnötigen Details oder Beschreibungen 
    - Sprich knapp und direkt, max. 15-20 Wörter
    - Vermeide Abkürzungen, Zahlen als Ziffern, komplexe Satzzeichen

    ALLGEMEINER STIL:
    - Direkte Ansprache des Benutzers
    - Keine unnötigen Formalitäten, komm direkt zum Punkt
    - Respektvoll aber freundlich
    - Eine Prise Humor ist erlaubt, aber nicht übertreiben
    - Optimiere für GEHÖRTES Verständnis, nicht für Lesekomfort
    """
    )

    WORKFLOW_SPECIFIC_PROMPT: ClassVar[str] = ""

    def __init__(
        self,
        speak_responses=True,
        tools: Optional[List[BaseTool]] = None,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        self.speak_responses = speak_responses
        self.tools = tools or []
        self.model_name = model_name or DEFAULT_LLM_MODEL
        self.graph_builder = StateGraph(State)

        self.speech_service = SpeechService(voice="nova")

        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = self._build_system_prompt()

        self.llm = ChatAnthropic(
            model=self.model_name, model_kwargs={"system": self.system_prompt}
        )

        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.memory = MemorySaver()

    def _build_system_prompt(self) -> str:
        """Baut den vollständigen Systemprompt aus den Komponenten zusammen."""
        if self.WORKFLOW_SPECIFIC_PROMPT:
            return f"{self.BASE_SYSTEM_PROMPT}\n\nWORKFLOW-SPEZIFISCHE ANWEISUNGEN:\n{self.WORKFLOW_SPECIFIC_PROMPT}"
        return self.BASE_SYSTEM_PROMPT

    def build_graph(self):
        """
        Baut den Graphen mit Standardknoten auf.
        """

        def chatbot(state: Dict[str, Any]) -> Dict[str, Any]:
            message = self.llm_with_tools.invoke(state["messages"])
            return {"messages": [message]}

        self.graph_builder.add_node("chatbot", chatbot)

        tool_node = ToolNode(tools=self.tools)
        self.graph_builder.add_node("tools", tool_node)

        self.graph_builder.add_conditional_edges(
            "chatbot",
            tools_condition,
        )

        self.graph_builder.add_edge("tools", "chatbot")
        self.graph_builder.set_entry_point("chatbot")

        return self.graph_builder.compile(checkpointer=self.memory)

    # TODO: Die arun und run methoden können wir langfristig loswerden:
    def run(
        self, input_message: str, thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        graph = self.build_graph()
        config = {"configurable": {"thread_id": thread_id or "1"}}

        final_message = None
        events = graph.stream(
            {"messages": [{"role": "user", "content": input_message}]},
            config,
            stream_mode="values",
        )

        for event in events:
            if "messages" in event:
                final_message = event["messages"][-1]
                final_message.pretty_print()

        return final_message.content

    async def arun(self, input_message: str, thread_id: Optional[str] = None) -> str:
        graph = self.build_graph()
        config = {"configurable": {"thread_id": thread_id or "1"}}

        last_message = None
        events = graph.astream(
            {"messages": [{"role": "user", "content": input_message}]},
            config,
            stream_mode="values",
        )

        async for event in events:
            if "messages" in event and isinstance(event["messages"], list):

                message = event["messages"][-1]
                message.pretty_print()

                if event["messages"] and isinstance(event["messages"][-1], AIMessage):

                    # Textinhalt extrahieren
                    content = None

                    if isinstance(message.content, list):
                        content = next(
                            (
                                item["text"]
                                for item in message.content
                                if item.get("type") == "text"
                            ),
                            None,
                        )
                    elif isinstance(message.content, str):
                        content = message.content

                    if content and content != last_message:
                        last_message = content
                        self.logger.info(f"AI-Nachricht: {content}")

                        # SpeechService mit der neuen Nachricht füttern

                        if self.speak_responses:
                            self.speech_service.enqueue_text(content, False)

        if last_message:
            return last_message
        else:
            self.logger.warning("Keine AI-Nachricht erhalten")
            return ""
