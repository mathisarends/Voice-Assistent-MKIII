from typing import Dict, Any
import textwrap
from langchain_openai import ChatOpenAI

from config.settings import GPT_MINI
from graphs.base_graph import BaseGraph
from graphs.workflow_registry import WorkflowRegistry

class WorkflowDispatcher:
    """Dispatcher für Anfragen an passende Workflows."""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or GPT_MINI
        self.llm = ChatOpenAI(model=self.model_name)
    
    async def dispatch(self, user_message: str) -> Dict[str, Any]:
        workflow_names = WorkflowRegistry.get_workflow_names()
        workflow_names_str = ", ".join(workflow_names) + ", default" # Komma getrennt und "default" am Ende

        prompt = textwrap.dedent(f"""
            Du bist ein Workflow-Auswahlspezialist. Wähle genau einen der verfügbaren Workflows basierend auf der Benutzeranfrage.

            Benutzeranfrage: {user_message}

            Verfügbare Workflows:
            {WorkflowRegistry.format_for_prompt()}
            Antworte NUR mit einem der folgenden Wörter: {workflow_names_str}.
            """)
        
        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        workflow_name = response.content.strip() if response and hasattr(response, "content") else "default"
        
        if workflow_name != "default" and workflow_name in WorkflowRegistry.get_all_workflows():
            return {"workflow": workflow_name}
        
        return {"workflow": "default"}
    
    async def run_workflow(self, workflow_name: str, user_message: str, thread_id: str = None) -> Any:
        if workflow_name == "default":
            response = await self.llm.ainvoke([{"role": "user", "content": user_message}])
            print(f"[DEFAULT] Antwort: {response.content[:100]}...")
            return response.content
        
        workflow_class = WorkflowRegistry.get_workflow(workflow_name)
        if workflow_class:
            print(f"[DISPATCHER] Starte Workflow: {workflow_name}")
            workflow: BaseGraph = workflow_class()
            return await workflow.arun(user_message, thread_id or workflow_name)

        return (await self.llm.ainvoke([{"role": "user", "content": user_message}])).content