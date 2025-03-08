from graphs.workflow_dispatcher import WorkflowDispatcher
from graphs.workflow_registry import WorkflowRegistry
from graphs.workflows.research_workflow import ResearchWorkflow
from graphs.workflows.document_workflow import DocumentWorkflow

def register_workflows():
    """Registriert alle verfügbaren Workflows in der Registry."""
    WorkflowRegistry.register(
        "research", 
        ResearchWorkflow,
        "Recherchiert Informationen im Web und erstellt ein Dokument",
        ["Websuche", "Dokumentenerstellung", "Markdown"]
    )
    
    WorkflowRegistry.register(
        "document", 
        DocumentWorkflow,
        "Erstellt Dokumente und Zusammenfassungen ohne externe Recherche",
        ["Dokumentenerstellung", "Markdown", "Formatierung"]
    )

def demo_dispatcher():
    """Demonstriert die Verwendung des Dispatchers für intelligentes Routing."""
    print("\n=== DEMO: Workflow-Dispatcher ===")
    
    dispatcher = WorkflowDispatcher()
    
    queries = [
        "Recherchiere die neuesten Informationen zu LangGraph und erstelle eine Zusammenfassung",
        "Erstelle mir ein schönes Markdown-Dokument mit den wichtigsten Python-Libraries für KI",
        "Was ist der Unterschied zwischen LangChain und LangGraph?",
    ]
    
    for i, query in enumerate(queries):
        print(f"\n--- Anfrage {i+1}: {query} ---")
        result = dispatcher.dispatch(query)
        selected_workflow = result["workflow"]
        print(f"Ausgewählter Workflow: {selected_workflow}")
        
        # Workflow ausführen (bei Bedarf kann das auskommentiert werden)
        # dispatcher.run_workflow(selected_workflow, query, f"demo_{i}")

def demo_direct_workflows():
    """Demonstriert den direkten Aufruf von Workflows (wie bisher)."""
    print("=== DEMO: Direkter Workflow-Aufruf ===")
    
    print("\n=== Beispiel: Recherche-Workflow ===")
    research_workflow = ResearchWorkflow()
    research_query = "Recherchiere Informationen zu Langgraph und schreibe mir einen Artikel in Markdown, den du dann in die Zwischenablage ablegst."
    research_workflow.run(research_query, "research_1")
    
    print("\n=== Beispiel: Dokumentations-Workflow ===")
    document_workflow = DocumentWorkflow()
    document_query = "Erstelle mir eine Markdown-Zusammenfassung über die wichtigsten Features von LangChain und lege sie in der Zwischenablage ab."
    document_workflow.run(document_query, "document_1")


def main():
    register_workflows()
    
    # Demo: Dispatcher für intelligentes Routing
    demo_dispatcher()
    
    
if __name__ == "__main__":
    main()