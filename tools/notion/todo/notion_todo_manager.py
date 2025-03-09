import asyncio
import json
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Callable, Union

from tools.notion.core.abstract_notion_client import AbstractNotionClient
from tools.notion.core.notion_pages import NotionPages

from dotenv import load_dotenv
load_dotenv()


class TodoPriority(Enum):
    DAILY_TOP_TASK = "Daily Top Task"
    HIGH = "Hoch"
    MEDIUM = "Mittel"
    LOW = "Niedrig"
    
    @classmethod
    def get_order(cls) -> Dict[str, int]:
        return {
            cls.DAILY_TOP_TASK.value: 1,
            cls.HIGH.value: 2,
            cls.MEDIUM.value: 3,
            cls.LOW.value: 4
        }


class TodoStatus(Enum):
    NOT_STARTED = "Nicht begonnen"
    IN_PROGRESS = "In Bearbeitung"
    DONE = "Erledigt"


@dataclass
class Todo:
    id: str
    title: str
    priority: str
    status: str
    done: bool
    project_ids: List[str]
    project_names: List[str]
    
    def format(self, index: Optional[int] = None) -> str:
        """Format a todo item for display"""
        prefix = f"{index + 1}. " if index is not None else ""
        result = f"{prefix}{self.title} (Priorität: {self.priority}, Status: {self.status}"
        
        if self.project_names:
            projects_str = ", ".join(self.project_names)
            result += f", Projekte: {projects_str}"
        
        result += ")"
        return result


class NotionTodoRepository:
    """Repository for interacting with Notion Todo database"""
    
    def __init__(self, client: AbstractNotionClient, database_id: str):
        self.client = client
        self.database_id = database_id
    
    async def fetch_all_todos(self) -> List[Dict[str, Any]]:
        """Fetch all todos from Notion database"""
        response = await self.client._make_request("post", f"databases/{self.database_id}/query")
        return response.json().get("results", [])
    
    async def create_todo(self, todo: Todo) -> Dict[str, Any]:
        """Create a new todo in Notion"""
        data = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Titel": {"title": [{"text": {"content": todo.title}}]},
                "Priorität": {"select": {"name": todo.priority}},
                "Status": {"status": {"name": todo.status}},
                "Fertig": {"checkbox": todo.done}
            }
        }
        
        # Add project relations if they exist
        if todo.project_ids:
            data["properties"]["Projekt"] = {
                "relation": [{"id": project_id} for project_id in todo.project_ids]
            }
            
        response = await self.client._make_request("post", "pages", data)
        return response.json() if response.status_code == 200 else None
    
    async def delete_todo(self, todo_id: str) -> bool:
        """Delete a todo by ID"""
        response = await self.client._make_request("delete", f"pages/{todo_id}")
        return response.status_code == 200


class TodoMapper:
    """Maps between Notion API format and Todo objects"""
    
    @staticmethod
    def from_notion(item: Dict[str, Any]) -> Optional[Todo]:
        """Convert a Notion API response to a Todo object"""
        try:
            properties = item.get("properties", {})
            
            # Extract title
            title_content = properties.get("Titel", {}).get("title", [])
            title = "Untitled Task"
            if title_content and len(title_content) > 0:
                title = title_content[0].get("text", {}).get("content", "Untitled Task")
            
            # Extract priority
            priority = properties.get("Priorität", {}).get("select", {})
            priority_name = priority.get("name", TodoPriority.MEDIUM.value) if priority else TodoPriority.MEDIUM.value
            
            # Extract status
            status = properties.get("Status", {}).get("status", {})
            status_name = status.get("name", TodoStatus.NOT_STARTED.value) if status else TodoStatus.NOT_STARTED.value
            
            # Extract done flag
            done = properties.get("Fertig", {}).get("checkbox", False)
            
            # Extract project relations
            project_relation = properties.get("Projekt", {}).get("relation", [])
            project_ids = [relation.get("id") for relation in project_relation if relation.get("id")]
            
            # Map project IDs to names
            project_names = []
            for project_id in project_ids:
                project_name = NotionPages.get_project_name_by_id(project_id)
                if project_name != "UNKNOWN_PROJECT":
                    project_names.append(project_name)
            
            return Todo(
                id=item.get("id", ""),
                title=title,
                priority=priority_name,
                status=status_name,
                done=done,
                project_ids=project_ids,
                project_names=project_names
            )
        except Exception as e:
            print(f"Error mapping Notion item to Todo: {e}")
            return None


class TodoService:
    """Business logic for Todo operations"""
    
    def __init__(self, repository: NotionTodoRepository, logger: Optional[Callable] = None):
        self.repository = repository
        self.logger = logger or print
    
    async def add_todo(self, title: str, priority: str = TodoPriority.MEDIUM.value, 
                       project_name: Optional[str] = None) -> str:
        """Add a new todo"""
        try:
            # Create a new Todo object
            project_ids = []
            if project_name:
                project_id = NotionPages.get_page_id(project_name)
                if project_id != "UNKNOWN_PROJECT":
                    project_ids = [project_id]
            
            todo = Todo(
                id="",  # Will be assigned by Notion
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
        """Get todos for a specific project"""
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
        """Get filtered and sorted todos"""
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
        """Delete completed todos"""
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
        """Format a list of todos for display"""
        if not todos:
            return "Keine offenen TODOs vorhanden."

        return "\n".join(todo.format(i) for i, todo in enumerate(todos))
    
    def log_info(self, message: str) -> None:
        """Log an info message"""
        if callable(self.logger):
            self.logger(message)
        else:
            print(message)
    
    def log_error(self, message: str) -> None:
        """Log an error message"""
        if callable(self.logger):
            self.logger(message)
        else:
            print(message)


class NotionTodoManager:
    """Facade for interacting with Notion Todos"""
    
    def __init__(self):
        self.client = AbstractNotionClient()
        self.database_id = NotionPages.get_database_id("TODOS")
        self.repository = NotionTodoRepository(self.client, self.database_id)
        self.service = TodoService(self.repository, logger=self._get_logger)
    
    async def add_todo(self, title: str, priority: str = TodoPriority.MEDIUM.value) -> str:
        """Add a new todo"""
        return await self.service.add_todo(title, priority)
    
    async def get_all_todos(self) -> str:
        """Get all todos"""
        return await self.service.get_all_todos()
    
    async def get_daily_top_tasks(self) -> str:
        """Get daily top tasks"""
        return await self.service.get_daily_top_tasks()
    
    async def get_todos_by_project(self, project_name: Optional[str] = None) -> str:
        """Get todos for a specific project"""
        return await self.service.get_todos_by_project(project_name)
    
    def _get_logger(self, message: str) -> None:
        """Get a logger function"""
        if hasattr(self, 'logger') and self.logger:
            if callable(message):
                self.logger.info(message)
            else:
                self.logger.info(lambda: message)
        else:
            print(message)


async def main():
    """Example usage"""
    notion_todo_manager = NotionTodoManager()
    
    # Examples of different calls:
    # print(await notion_todo_manager.get_all_todos())
    # print(await notion_todo_manager.get_daily_top_tasks())
    
    # Get TODOs for a project by name
    print("TODOs für JARVIS_PROJECT:")
    print(await notion_todo_manager.get_todos_by_project(project_name="JARVIS_PROJECT"))
    
    # Example of adding a new TODO
    # print(await notion_todo_manager.add_todo("Test TODO", TodoPriority.HIGH.value))
    

if __name__ == "__main__":
    asyncio.run(main())