from typing import List, Dict, Any, TypedDict, Optional, NotRequired
from config.notion_config import NOTION_DATABASES
from tools.notion.core.abstract_notion_client import AbstractNotionClient
from langchain_anthropic import ChatAnthropic
from config.settings import DEFAULT_LLM_MODEL


class ProjectInfo(TypedDict):
    id: str
    name: str
    raw_data: NotRequired[Any]


class NotionProjectsRepository(AbstractNotionClient):

    def __init__(self, model_name: str = None):
        super().__init__()
        self.projects_database_id = NOTION_DATABASES["PROJECTS"]
        self.model_name = model_name or DEFAULT_LLM_MODEL
        self.llm = ChatAnthropic(model=self.model_name)

    async def get_all_projects(self) -> List[Dict[str, Any]]:
        response = await self._make_request(
            "post", "databases/" + self.projects_database_id + "/query", {}
        )

        if response.status_code != 200:
            self.logger.error(f"Error retrieving projects: {response.text}")
            return []

        projects = response.json().get("results", [])

        formatted_projects = []
        for project in projects:
            title = self._extract_page_title(project)
            project_id = project["id"]

            formatted_projects.append(
                {"id": project_id, "name": title, "raw_data": project}
            )

        return formatted_projects

    async def identify_project_with_llm(self, user_query: str) -> ProjectInfo:
        """Identifiziert das passende Projekt mit Hilfe eines LLM basierend auf der Benutzeranfrage."""
        all_projects = await self.get_all_projects()

        if not all_projects:
            return None

        projects_list = "\n".join(
            [f"- ID: {p['id']}, Name: {p['name']}" for p in all_projects]
        )

        prompt = f"""
        Deine Aufgabe ist es, aus dem Benutzer-Input das richtige Notion-Projekt zu identifizieren.

        Benutzer-Input: "{user_query}"
        
        Verfügbare Projekte:
        {projects_list}
        
        Analysiere, welches Projekt am besten zu der Anfrage passt. Der Benutzer will Informationen in einem bestimmten Projekt speichern.
        
        Gib NUR die ID des passenden Projekts zurück. Nichts anderes. Kein erklärender Text, keine Formatierung, nur die ID.
        Falls kein passendes Projekt gefunden werden kann, gib "keine_übereinstimmung" zurück.
        """

        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages)

        project_id = response.content.strip()

        for project in all_projects:
            if project["id"] == project_id:
                return project

        return None

    def _extract_page_title(self, page):
        """Extrahiert den Titel aus einem Seitenobjekt."""
        if "properties" in page and "title" in page.get("properties", {}):
            title_prop = page["properties"].get("title", {})
            if "title" in title_prop and title_prop["title"]:
                return title_prop["title"][0]["text"]["content"]

        if "properties" in page:
            for prop_name, prop_value in page["properties"].items():
                if prop_value.get("type") == "title" and prop_value.get("title"):
                    return prop_value["title"][0]["text"]["content"]

        if "title" in page:
            title_array = page.get("title", [])
            if title_array:
                return title_array[0]["text"]["content"]

        return "Unnamed Page"


async def example_usage():
    """Zeigt die Verwendung des NotionProjectsRepository mit LLM."""
    repo = NotionProjectsRepository()

    all_projects = await repo.get_all_projects()
    print(f"Gefundene Projekte: {len(all_projects)}")
    for project in all_projects:
        print(f"- {project['name']} (ID: {project['id']})")

    user_query = "Speichere Informationen über das neue Browser-Use Framework in meinem Jarvis-Projekt"
    project = await repo.identify_project_with_llm(user_query)

    if project:
        print(f"\nIdentifiziertes Projekt: {project['name']} (ID: {project['id']})")
    else:
        print("\nKein passendes Projekt gefunden.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_usage())
