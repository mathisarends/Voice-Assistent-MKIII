from typing import Optional
from graphs.base_graph import BaseGraph
from tools.notion.todo.notion_todo_tools import NotionAddTodoTool, NotionGetDailyTopTasksTool, NotionGetTodosByProjectTool

# Kleinen Graphen für den get Tasks by Project.
class NotionTodoWorkflow(BaseGraph):
    """Ein Workflow für Recherche und Dokumentation."""
    
    def __init__(self, model_name: Optional[str] = None):
        notion_add_todo_tool = NotionAddTodoTool()
        notion_get_todos_by_project_tool = NotionGetTodosByProjectTool()
        notion_get_daily_top_tasks_tool = NotionGetDailyTopTasksTool()

        tools = [notion_add_todo_tool, notion_get_todos_by_project_tool, notion_get_daily_top_tasks_tool]
        
        super().__init__(tools, model_name)

if __name__ == "__main__":
    notion_todo_workflow = NotionTodoWorkflow()
    notion_todo_workflow.run(input_message="Gebe mir bitte meine heutigen wichtigen Aufgaben", thread_id="todo_1")