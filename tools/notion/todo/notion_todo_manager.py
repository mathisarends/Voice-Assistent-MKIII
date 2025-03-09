

import asyncio
from typing import Optional
from tools.notion.core.abstract_notion_client import AbstractNotionClient
from tools.notion.core.notion_pages import NotionPages
from tools.notion.todo.notion_todo_repository import NotionTodoRepository
from tools.notion.todo.todo_models import TodoPriority
from tools.notion.todo.todo_service import TodoService

class NotionTodoManager:
    """Facade for interacting with Notion Todos"""
    
    def __init__(self):
        self.client = AbstractNotionClient()
        self.database_id = NotionPages.get_database_id("TODOS")
        self.repository = NotionTodoRepository(self.client, self.database_id)
        self.logger = None  
        self.service = TodoService(self.repository, logger=self._get_logger)
    
    async def add_todo(self, title: str, priority: str = TodoPriority.MEDIUM.value) -> str:
        return await self.service.add_todo(title, priority)
    
    async def get_all_todos(self) -> str:
        return await self.service.get_all_todos()
    
    async def get_daily_top_tasks(self) -> str:
        return await self.service.get_daily_top_tasks()
    
    async def get_todos_by_project(self, project_name: Optional[str] = None) -> str:
        return await self.service.get_todos_by_project(project_name)
    
    def set_logger(self, logger):
        self.logger = logger
    
    def _get_logger(self, message: str) -> None:
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