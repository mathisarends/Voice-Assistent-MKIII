import asyncio
from typing import Optional, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from tools.notion.todo.notion_todo_manager import NotionTodoManager
from tools.notion.todo.todo_models import TodoPriority

# TODO_ Die hier in weiter Domänen aufspeichern.


class GetTodosByProjectInput(BaseModel):
    project_name: str = Field(
        description="Der Name des Projekts, für das TODOs abgefragt werden sollen"
    )


class GetDailyTopTasksInput(BaseModel):
    """Eingabemodell für die Abfrage der Daily Top Tasks."""

    pass  # Keine Parameter erforderlich


class AddTodoInput(BaseModel):
    title: str = Field(description="Der Titel des neuen TODOs")
    priority: str = Field(
        default=TodoPriority.MEDIUM.value,
        description=f"Die Priorität des TODOs. Mögliche Werte: {', '.join([p.value for p in TodoPriority])}",
    )
    project_name: Optional[str] = Field(
        default=None,
        description="Optional: Der Name des Projekts, zu dem das TODO gehört",
    )


class NotionGetTodosByProjectTool(BaseTool):
    name: str = "notion_get_todos_by_project"
    description: str = "Gibt eine Liste aller TODOs für ein bestimmtes Projekt zurück."
    args_schema: Type[BaseModel] = GetTodosByProjectInput

    todo_manager: NotionTodoManager = Field(
        default_factory=NotionTodoManager, exclude=True
    )

    def _run(self, project_name: str) -> str:
        return asyncio.run(self._arun(project_name))

    async def _arun(self, project_name: str) -> str:
        try:
            return await self.todo_manager.get_todos_by_project(project_name)
        except Exception as e:
            return f"Fehler bei der Abfrage der Projekt-TODOs: {str(e)}"


class NotionGetDailyTopTasksTool(BaseTool):
    name: str = "notion_get_daily_top_tasks"
    description: str = (
        "Gibt eine Liste aller täglichen Top-Aufgaben (Daily Top Tasks) zurück."
    )
    args_schema: Type[BaseModel] = GetDailyTopTasksInput

    todo_manager: NotionTodoManager = Field(
        default_factory=NotionTodoManager, exclude=True
    )

    def _run(self) -> str:
        return asyncio.run(self._arun())

    async def _arun(self) -> str:
        try:
            return await self.todo_manager.get_daily_top_tasks()
        except Exception as e:
            return f"Fehler bei der Abfrage der Daily Top Tasks: {str(e)}"


class NotionAddTodoTool(BaseTool):
    name: str = "notion_add_todo"
    description: str = "Fügt ein neues TODO zur Notion-Datenbank hinzu."
    args_schema: Type[BaseModel] = AddTodoInput

    todo_manager: NotionTodoManager = Field(
        default_factory=NotionTodoManager, exclude=True
    )

    def _run(self, title: str) -> str:
        return asyncio.run(self._arun(title))

    async def _arun(self, title: str) -> str:
        try:
            return await self.todo_manager.add_todo(title)
        except Exception as e:
            return f"Fehler beim Hinzufügen des TODOs: {str(e)}"

def get_notion_todo_tools():
    notion_add_todo_tool = NotionAddTodoTool()
    notion_get_todos_by_project_tool = NotionGetTodosByProjectTool()
    notion_get_daily_top_tasks_tool = NotionGetDailyTopTasksTool()
    
    return [
        notion_add_todo_tool,
        notion_get_todos_by_project_tool,
        notion_get_daily_top_tasks_tool,
    ]