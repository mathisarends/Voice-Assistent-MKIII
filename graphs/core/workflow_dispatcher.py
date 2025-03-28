import textwrap
from typing import Any, Dict, TypedDict

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from config.settings import GEMINI_FLASH
from graphs.core.workflow_audio_feedback_observer import (
    WorkflowAudioFeedbackObserver, WorkflowObserver)
from graphs.core.workflow_registry import WorkflowRegistry
from service.speech_service import SpeechService
from util.loggin_mixin import LoggingMixin


class WorkflowState(TypedDict):
    user_message: str
    workflow: str
    response: str
    thread_id: str
    task_done: bool


class WorkflowDispatcher(LoggingMixin):
    def __init__(self, model_name: str = None):
        self.model_name = model_name or GEMINI_FLASH
        self.speech_service = SpeechService(voice="nova")

        self.observers = [WorkflowAudioFeedbackObserver()]

        # Graph definieren
        workflow_graph = StateGraph(WorkflowState)

        # Knoten hinzufügen
        workflow_graph.add_node("select_workflow", self._select_workflow)
        workflow_graph.add_node("default_workflow", self._run_default_workflow)
        workflow_graph.add_node("specific_workflow", self._run_specific_workflow)

        # Den Startpunkt setzen
        workflow_graph.set_entry_point("select_workflow")

        workflow_graph.add_conditional_edges(
            "select_workflow",
            self._router,
            {
                "default_workflow": "default_workflow",
                "specific_workflow": "specific_workflow",
            },
        )

        workflow_graph.add_edge("default_workflow", END)
        workflow_graph.add_edge("specific_workflow", END)

        # Compiler
        self.graph = workflow_graph.compile()

    async def _select_workflow(self, state: WorkflowState) -> WorkflowState:
        # Gemini für schnellere Verarbeitung verwenden
        llm = ChatGoogleGenerativeAI(
            model=self.model_name, temperature=0.0, max_output_tokens=20
        )
        workflow_names = WorkflowRegistry.get_workflow_names()
        workflow_names_str = ", ".join(workflow_names) + ", default"

        prompt = textwrap.dedent(
            f"""
            Du bist ein Workflow-Auswahlspezialist. Wähle genau einen der verfügbaren Workflows basierend auf der Benutzeranfrage.

            Benutzeranfrage: {state["user_message"]}

            Verfügbare Workflows:
            {WorkflowRegistry.format_for_prompt()}
            Antworte NUR mit einem der folgenden Wörter: {workflow_names_str}.
            """
        )

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        workflow_name = (
            response.content.strip()
            if response and hasattr(response, "content")
            else "default"
        )

        if (
            workflow_name != "default"
            and workflow_name in WorkflowRegistry.get_all_workflows()
        ):
            state["workflow"] = workflow_name
        else:
            state["workflow"] = "default"

        self._notify_workflow_selected(state["workflow"], state)

        return state

    async def _run_default_workflow(self, state: WorkflowState) -> WorkflowState:
        # Hier auch Gemini verwenden
        llm = ChatGoogleGenerativeAI(model=self.model_name)
        response = await llm.ainvoke([HumanMessage(content=state["user_message"])])
        state["response"] = response.content
        self.logger.info(f"[DEFAULT] Antwort: {response.content[:100]}...")
        return state

    async def _run_specific_workflow(self, state: WorkflowState) -> WorkflowState:
        workflow_class = WorkflowRegistry.get_workflow(state["workflow"])

        if workflow_class is None:
            return state

        self.logger.info(f"[DISPATCHER] Starte Workflow: {state['workflow']}")
        workflow: BaseGraph = workflow_class()
        thread_id = state.get("thread_id") or state["workflow"]

        response = await workflow.arun(state["user_message"], thread_id)
        state["response"] = response

        return state

    def _router(self, state: WorkflowState) -> str:
        if state["workflow"] == "default":
            return "default_workflow"

        return "specific_workflow"

    async def dispatch(
        self, user_message: str, thread_id: str = None
    ) -> Dict[str, Any]:
        """Dispatcht eine Anfrage an den passenden Workflow."""
        state = {
            "user_message": user_message,
            "workflow": "",
            "response": "",
            "thread_id": thread_id or "",
        }

        result = await self.graph.ainvoke(state)
        return {"workflow": result["workflow"], "response": result["response"]}

    def add_observer(self, observer: WorkflowObserver) -> None:
        self.observers.append(observer)

    def remove_observer(self, observer: WorkflowObserver) -> None:
        if observer in self.observers:
            self.observers.remove(observer)

    def _notify_workflow_selected(
        self, workflow_name: str, context: Dict[str, Any]
    ) -> None:
        for observer in self.observers:
            observer.on_workflow_selected(workflow_name, context)
