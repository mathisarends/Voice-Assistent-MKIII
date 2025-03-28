from typing import Any, Dict, Optional

from tools.notion.core.notion_pages import NotionPages
from tools.notion.todo.todo_models import Todo, TodoPriority, TodoStatus


class TodoMapper:
    """Maps between Notion API format and Todo objects"""

    @staticmethod
    def from_notion(item: Dict[str, Any]) -> Optional[Todo]:
        """Convert a Notion API response to a Todo object"""
        try:
            properties = item.get("properties", {})

            title_content = properties.get("Titel", {}).get("title", [])
            title = "Untitled Task"
            if title_content and len(title_content) > 0:
                title = title_content[0].get("text", {}).get("content", "Untitled Task")

            priority = properties.get("Priorität", {}).get("select", {})
            priority_name = (
                priority.get("name", TodoPriority.MEDIUM.value)
                if priority
                else TodoPriority.MEDIUM.value
            )

            status = properties.get("Status", {}).get("status", {})
            status_name = (
                status.get("name", TodoStatus.NOT_STARTED.value)
                if status
                else TodoStatus.NOT_STARTED.value
            )

            done = properties.get("Fertig", {}).get("checkbox", False)

            project_relation = properties.get("Projekt", {}).get("relation", [])
            project_ids = [
                relation.get("id")
                for relation in project_relation
                if relation.get("id")
            ]

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
                project_names=project_names,
            )
        except Exception as e:
            print(f"Error mapping Notion item to Todo: {e}")
            return None
