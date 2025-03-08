
from graphs.workflows.research_workflow import ResearchWorkflow
from graphs.workflows.document_workflow import DocumentWorkflow

def main():
    """Hauptfunktion, die verschiedene Workflows demonstriert."""
    
    print("=== Beispiel: Recherche-Workflow ===")
    research_workflow = ResearchWorkflow()
    research_query = "Recherchiere Informationen zu Langgraph und schreibe mir einen Artikel in Markdown, den du dann in die Zwischenablage ablegst."
    research_workflow.run(research_query, "research_1")
    
    print("\n=== Beispiel: Dokumentations-Workflow ===")
    document_workflow = DocumentWorkflow()
    document_query = "Erstelle mir eine Markdown-Zusammenfassung über die wichtigsten Features von LangChain und lege sie in der Zwischenablage ab."
    document_workflow.run(document_query, "document_1")

if __name__ == "__main__":
    main()