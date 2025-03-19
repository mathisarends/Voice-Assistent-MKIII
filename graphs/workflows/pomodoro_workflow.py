from typing import Optional
from graphs.base_graph import BaseGraph
from tools.notion.todo.notion_todo_tools import NotionAddTodoTool, NotionGetDailyTopTasksTool, NotionGetTodosByProjectTool
from tools.pomodoro.pomodoro_tools import get_pomodoro_tools

# TODO: Workflow ausgestalten udn mit Zustandsbasierten Verfahren ergänzen auch spotify berücksichtigen hier:
class PomodoroWorkflow(BaseGraph):
    """Ein Workflow für Recherche und Dokumentation."""
    
    def __init__(self, model_name: Optional[str] = None):
        tools = get_pomodoro_tools()  # Ohne die zusätzlichen eckigen Klammern
        super().__init__(speak_responses=False, tools=tools, model_name=model_name)