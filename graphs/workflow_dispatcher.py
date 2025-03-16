from typing import Dict, Any
from langchain_anthropic import ChatAnthropic

from config.settings import DEFAULT_LLM_MODEL
from graphs.workflow_registry import WorkflowRegistry


class WorkflowDispatcher:
    """Dispatcher für Anfragen an passende Workflows."""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or DEFAULT_LLM_MODEL
        self.llm = ChatAnthropic(model=self.model_name)
    
    def dispatch(self, user_message: str) -> Dict[str, Any]:
        """
        Entscheidet basierend auf der Benutzeranfrage, welcher Workflow verwendet werden soll.
        
        Args:
            user_message: Die Anfrage des Benutzers
            
        Returns:
            Dictionary mit dem Namen des zu verwendenden Workflows
        """
        prompt = f"""
        Du bist ein Workflow-Auswahlspezialist. Wähle genau einen der verfügbaren Workflows basierend auf der Benutzeranfrage.

        Benutzeranfrage: {user_message}

        Verfügbare Workflows:
        {WorkflowRegistry.format_for_prompt()}

        WICHTIG: 
        - Der "research"-Workflow sollte NUR gewählt werden, wenn EXTERNE Informationsquellen benötigt werden.
        - Der "document"-Workflow sollte gewählt werden, wenn es um Dokumentenerstellung mit BEREITS BEKANNTEM Wissen geht.
        - Wähle "default", wenn keiner der Workflows passend ist oder wenn die Anfrage mit allgemeinem Wissen beantwortet werden kann.

        Antworte NUR mit einem der folgenden Wörter: "research", "document" oder "default".
        """
        
        # LLM nach dem passenden Workflow fragen
        workflow_name = self.llm.invoke([{"role": "user", "content": prompt}]).content.strip()
        
        print("WorkflowRegistry.get_all_workflows()", WorkflowRegistry.get_all_workflows())
        
        if workflow_name != "default" and workflow_name in WorkflowRegistry.get_all_workflows():
            return {"workflow": workflow_name}
        
        return {"workflow": "default"}
    
    async def run_workflow(self, workflow_name: str, user_message: str, thread_id: str = None) -> Any:
        """
        Führt den angegebenen Workflow mit der Benutzeranfrage asynchron aus.
        
        Args:
            workflow_name: Name des auszuführenden Workflows
            user_message: Die Anfrage des Benutzers
            thread_id: Optional. Eine eindeutige Thread-ID
            
        Returns:
            Das Ergebnis der Workflow-Ausführung oder eine Standardantwort
        """
        if workflow_name == "default":
            response = await self.llm.ainvoke([{"role": "user", "content": user_message}])
            print(f"[DEFAULT] Antwort: {response.content[:100]}...")
            return response.content
        
        workflow_class = WorkflowRegistry.get_workflow(workflow_name)
        if workflow_class:
            print(f"[DISPATCHER] Starte Workflow: {workflow_name}")
            workflow = workflow_class()
            return await workflow.arun(user_message, thread_id or workflow_name)

        return (await self.llm.ainvoke([{"role": "user", "content": user_message}])).content