from typing import Any, Dict, List
from tools.notion.core.abstract_notion_client import AbstractNotionClient
from tools.notion.todo.todo_models import Todo


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