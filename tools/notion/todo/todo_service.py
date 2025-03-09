import asyncio
from typing import List, Optional, Callable

from tools.notion.core.notion_pages import NotionPages
from tools.notion.todo.notion_todo_repository import NotionTodoRepository
from tools.notion.todo.todo_mapper import TodoMapper
from tools.notion.todo.todo_models import Todo, TodoPriority, TodoStatus

class TodoService:
    """Business logic for Todo operations"""
    
    def __init__(self, repository: NotionTodoRepository, logger: Optional[Callable] = None):
        self.repository = repository
        self.logger = logger or print
    
    async def add_todo(self, title: str, priority: str = TodoPriority.MEDIUM.value, 
                       project_name: Optional[str] = None) -> str:
        """Add a new todo"""
        try:
            project_ids = []
            if project_name:
                project_id = NotionPages.get_page_id(project_name)
                if project_id != "UNKNOWN_PROJECT":
                    project_ids = [project_id]
            
            todo = Todo(
                id="",
                title=title,
                priority=priority,
                status=TodoStatus.NOT_STARTED.value,
                done=False,
                project_ids=project_ids,
                project_names=[project_name] if project_name and project_id != "UNKNOWN_PROJECT" else []
            )
            
            # Create in Notion
            result = await self.repository.create_todo(todo)
            
            if not result:
                log_message = f"❌ Error adding TODO: {title}"
                self.log_error(log_message)
                return log_message
                
            log_message = f"✅ TODO added: {title}"
            self.log_info(log_message)
            return f"✅ TODO '{title}' added successfully."
            
        except Exception as e:
            log_message = f"❌ API call failed: {str(e)}"
            self.log_error(log_message)
            return log_message
            
    async def get_all_todos(self) -> str:
        """Get all open todos"""
        try:
            await self._delete_completed_todos()
            todos = await self._get_filtered_todos()
            return self._format_todo_list(todos)
        except Exception as e:
            log_message = f"❌ API call failed: {str(e)}"
            self.log_error(log_message)
            return log_message
            
    async def get_daily_top_tasks(self) -> str:
        """Get all daily top tasks"""
        try:
            await self._delete_completed_todos()
            todos = await self._get_filtered_todos()
            daily_top_tasks = [todo for todo in todos if todo.priority == TodoPriority.DAILY_TOP_TASK.value]
            return self._format_todo_list(daily_top_tasks)
        except Exception as e:
            log_message = f"❌ API call failed: {str(e)}"
            self.log_error(log_message)
            return log_message
            
    async def get_todos_by_project(self, project_name: Optional[str] = None) -> str:
        try:
            if not project_name:
                return "❌ Kein Projektname angegeben"
                
            project_id = NotionPages.get_page_id(project_name)
            
            if project_id == "UNKNOWN_PROJECT":
                return f"❌ Unbekanntes Projekt: {project_name}"
                
            await self._delete_completed_todos()
            todos = await self._get_filtered_todos()
            
            # Filter by project ID
            project_todos = [todo for todo in todos if project_id in todo.project_ids]
            
            if not project_todos:
                return f"Keine offenen TODOs für Projekt '{project_name}' gefunden."
            
            return self._format_todo_list(project_todos)
            
        except Exception as e:
            log_message = f"❌ API call failed: {str(e)}"
            self.log_error(log_message)
            return log_message
    
    async def _get_filtered_todos(self) -> List[Todo]:
        try:
            results = await self.repository.fetch_all_todos()
            
            if not results:
                return []
            
            # Convert to Todo objects
            todos = []
            for item in results:
                # Skip completed todos
                if item.get("properties", {}).get("Fertig", {}).get("checkbox", True):
                    continue
                
                todo = TodoMapper.from_notion(item)
                if todo:
                    todos.append(todo)
            
            # Sort by priority
            priority_order = TodoPriority.get_order()
            return sorted(todos, key=lambda todo: priority_order.get(todo.priority, 99))
            
        except Exception as e:
            self.log_error(f"❌ API call failed: {str(e)}")
            return []
    
    async def _delete_completed_todos(self) -> None:
        try:
            results = await self.repository.fetch_all_todos()
            
            completed_todo_ids = [
                item.get("id") for item in results 
                if item.get("properties", {}).get("Fertig", {}).get("checkbox", False)
            ]
            
            if not completed_todo_ids:
                return
                
            delete_tasks = [self.repository.delete_todo(todo_id) for todo_id in completed_todo_ids]
            results = await asyncio.gather(*delete_tasks, return_exceptions=True)
            
            deleted_count = sum(1 for result in results if result is True)
            
            if deleted_count > 0:
                self.log_info(f"✅ {deleted_count} abgeschlossene TODOs gelöscht")
                
        except Exception as e:
            self.log_error(f"❌ Fehler beim Aufräumen der TODOs: {str(e)}")
    
    def _format_todo_list(self, todos: List[Todo]) -> str:
        if not todos:
            return "Keine offenen TODOs vorhanden."

        return "\n".join(todo.format(i) for i, todo in enumerate(todos))
    
    def log_info(self, message: str) -> None:
        if callable(self.logger):
            self.logger(message)
        else:
            print(message)
    
    def log_error(self, message: str) -> None:
        if callable(self.logger):
            self.logger(message)
        else:
            print(message)