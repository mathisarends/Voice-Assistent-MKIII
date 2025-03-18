from typing import Dict, Any, TypedDict, List
import textwrap
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from assistant.speech_service import SpeechService
from config.settings import GPT_MINI
from graphs.workflow_registry import WorkflowRegistry, register_workflows
from graphs.workflow_selected_observer import WorkflowAudioFeedbackObserver, WorkflowObserver
from util.loggin_mixin import LoggingMixin

class WorkflowState(TypedDict):
    user_message: str
    workflow: str
    response: str
    thread_id: str
    task_done: bool

class WorkflowDispatcher(LoggingMixin):
    def __init__(self, model_name: str = None):
        self.model_name = model_name or GPT_MINI
        
        self.speech_service = SpeechService()
                
        self.observers: List[WorkflowObserver] = []
        
        self.observers.append(WorkflowAudioFeedbackObserver())
        
        # Graph definieren
        workflow_graph = StateGraph(WorkflowState)
        
        # Knoten hinzufügen
        workflow_graph.add_node("select_workflow", self._select_workflow)
        workflow_graph.add_node("default_workflow", self._run_default_workflow)
        workflow_graph.add_node("specific_workflow", self._run_specific_workflow)
        
        # Den Startpunkt setzen
        workflow_graph.set_entry_point("select_workflow")
        
        # Router als Conditional Edge definieren
        workflow_graph.add_conditional_edges(
            "select_workflow",
            self._router,
            {
                "default_workflow": "default_workflow",
                "specific_workflow": "specific_workflow"
            }
        )
        
        # Ende definieren
        workflow_graph.add_edge("default_workflow", END)
        workflow_graph.add_edge("specific_workflow", END)
        
        # Compiler
        self.graph = workflow_graph.compile()
    
    async def _select_workflow(self, state: WorkflowState) -> WorkflowState:
        llm = ChatOpenAI(model=self.model_name)
        workflow_names = WorkflowRegistry.get_workflow_names()
        workflow_names_str = ", ".join(workflow_names) + ", default"

        prompt = textwrap.dedent(f"""
            Du bist ein Workflow-Auswahlspezialist. Wähle genau einen der verfügbaren Workflows basierend auf der Benutzeranfrage.

            Benutzeranfrage: {state["user_message"]}

            Verfügbare Workflows:
            {WorkflowRegistry.format_for_prompt()}
            Antworte NUR mit einem der folgenden Wörter: {workflow_names_str}.
            """)
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        workflow_name = response.content.strip() if response and hasattr(response, "content") else "default"
        
        if workflow_name != "default" and workflow_name in WorkflowRegistry.get_all_workflows():
            state["workflow"] = workflow_name
        else:
            state["workflow"] = "default"
            
        # self._notify_workflow_selected(state["workflow"], {"message": state["user_message"]})
        
        return state
    
    async def _run_default_workflow(self, state: WorkflowState) -> WorkflowState:
        llm = ChatOpenAI(model=self.model_name)
        response = await llm.ainvoke([HumanMessage(content=state["user_message"])])
        state["response"] = response.content
        self.logger.info(f"[DEFAULT] Antwort: {response.content[:100]}...")
        return state
    
    # async def _run_specific_workflow(self, state: WorkflowState) -> WorkflowState:
    #     workflow_class = WorkflowRegistry.get_workflow(state["workflow"])
    #     if workflow_class:
    #         self.logger.info(f"[DISPATCHER] Starte Workflow: {state['workflow']}")
    #         workflow = workflow_class()
    #         thread_id = state.get("thread_id") or state["workflow"]
    #         state["response"] = await workflow.arun(state["user_message"], thread_id)
    #     return state
    
    async def _run_specific_workflow(self, state: WorkflowState) -> WorkflowState:
        workflow_class = WorkflowRegistry.get_workflow(state["workflow"])
        if workflow_class:
            self.logger.info(f"[DISPATCHER] Starte Workflow: {state['workflow']}")
            workflow = workflow_class()
            thread_id = state.get("thread_id") or state["workflow"]

            # Collect all messages in a list
            messages = []
            async for message in workflow.arun_generator(state["user_message"], thread_id):
                self.logger.info("Message from assistatn: %s", message)
                messages.append(message)   
                self.speech_service.speak_response(message, is_interrupting=False)
            
            if messages:
                state["response"] = messages[-1]
                self.logger.info(f"[DISPATCHER] Finale AI-Antwort: {state['response']}")

        return state
    
    def _router(self, state: WorkflowState) -> str:
        if state["workflow"] == "default":
            return "default_workflow"
        
        return "specific_workflow"
    
    async def dispatch(self, user_message: str, thread_id: str = None) -> Dict[str, Any]:
        """Dispatcht eine Anfrage an den passenden Workflow."""
        state = {
            "user_message": user_message,
            "workflow": "",
            "response": "",
            "thread_id": thread_id or ""
        }
        
        result = await self.graph.ainvoke(state)
        return {
            "workflow": result["workflow"],
            "response": result["response"]
        }
    
    async def run_workflow(self, workflow_name: str, user_message: str, thread_id: str = None) -> Any:
        state = {
            "user_message": user_message,
            "workflow": workflow_name,
            "response": "",
            "thread_id": thread_id or workflow_name
        }
        
        if workflow_name == "default":
            result = await self._run_default_workflow(state)
        else:
            result = await self._run_specific_workflow(state)
            
        return result["response"]
    
    def add_observer(self, observer: WorkflowObserver) -> None:
        self.observers.append(observer)
    
    def remove_observer(self, observer: WorkflowObserver) -> None:
        if observer in self.observers:
            self.observers.remove(observer)
    
    def _notify_workflow_selected(self, workflow_name: str, context: Dict[str, Any]) -> None:
        for observer in self.observers:
            observer.on_workflow_selected(workflow_name, context)