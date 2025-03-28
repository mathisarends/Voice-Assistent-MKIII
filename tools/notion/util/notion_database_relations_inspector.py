import asyncio
from tools.notion.core.abstract_notion_client import AbstractNotionClient


class NotionProjectAssigner(AbstractNotionClient):
    """Utility to assign information to projects in Notion."""

    async def get_all_projects(self, projects_database_id):
        """Get all available projects from the projects database."""
        response = await self._make_request(
            "post", "databases/" + projects_database_id + "/query", {}
        )

        if response.status_code != 200:
            self.logger.error(f"Error retrieving projects: {response.text}")
            return f"Error retrieving projects: {response.text}"

        projects = response.json().get("results", [])
        return [
            {
                "id": project["id"],
                "name": self._extract_page_title(project),
                "properties": project.get("properties", {}),
            }
            for project in projects
        ]

    async def create_note_with_project(
        self, notes_database_id, title, content, project_id, tags=None, source=None
    ):
        """Create a new note in the notes database and link it to a project."""
        # Prepare properties
        properties = {
            "Name": {"title": [{"text": {"content": title}}]},
            "📁 Projekte": {"relation": [{"id": project_id}]},
        }

        # Add tags if provided
        if tags and isinstance(tags, list):
            properties["Tags"] = {"multi_select": [{"name": tag} for tag in tags]}

        # Add source if provided
        if source:
            properties["Quelle"] = {"rich_text": [{"text": {"content": source}}]}

        # Set status to "Entwurf" (Draft)
        properties["Status"] = {"status": {"name": "Entwurf"}}

        # Prepare the request body
        request_body = {
            "parent": {"database_id": notes_database_id},
            "properties": properties,
        }

        # Add content if provided
        if content:
            request_body["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    },
                }
            ]

        # Make the request to create the page
        response = await self._make_request("post", "pages", request_body)

        if response.status_code != 200:
            self.logger.error(f"Error creating note: {response.text}")
            return f"Error creating note: {response.text}"

        return response.json()

    async def search_projects(self, query, projects_database_id):
        """Search for projects by name."""
        all_projects = await self.get_all_projects(projects_database_id)

        if isinstance(all_projects, str):  # Error case
            return all_projects

        # Filter projects by query (case-insensitive)
        matching_projects = [
            project
            for project in all_projects
            if query.lower() in project["name"].lower()
        ]

        return matching_projects

    def _extract_page_title(self, page):
        """Extract the title from a page object."""
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

    def format_projects_list(self, projects):
        """Format a list of projects for display."""
        if isinstance(projects, str):
            return projects

        if not projects:
            return "Keine Projekte gefunden."

        result = ["Verfügbare Projekte:"]
        for i, project in enumerate(projects, 1):
            result.append(f"{i}. {project['name']} (ID: {project['id']})")

        return "\n".join(result)


async def interactive_assign_note_to_project():
    """Interactive function to assign a note to a project."""
    assigner = NotionProjectAssigner()

    # Database IDs
    NOTES_DATABASE_ID = "1a6389d5-7bd3-8097-aa38-e93cb052615a"  # Wissen & Notizen
    PROJECTS_DATABASE_ID = "1a6389d5-7bd3-80a3-a60e-cb6bc02f85d6"  # Projekte

    # Step 1: Search for a project
    print("=== Projekt-Suchfunktion ===")
    search_query = input("Projektnamen eingeben (oder Teil davon): ")

    matching_projects = await assigner.search_projects(
        search_query, PROJECTS_DATABASE_ID
    )

    if isinstance(matching_projects, str) or not matching_projects:
        print("Keine passenden Projekte gefunden. Bitte versuchen Sie es erneut.")
        return

    # Display matching projects
    print("\n" + assigner.format_projects_list(matching_projects))

    # Step 2: Select a project
    project_index = int(input("\nProjektnummer auswählen: ")) - 1
    if project_index < 0 or project_index >= len(matching_projects):
        print("Ungültige Auswahl.")
        return

    selected_project = matching_projects[project_index]
    print(f"\nAusgewähltes Projekt: {selected_project['name']}")

    # Step 3: Create a new note
    print("\n=== Neue Notiz erstellen ===")
    note_title = input("Titel der Notiz: ")
    note_content = input("Inhalt der Notiz (optional): ")
    note_source = input("Quelle (optional): ")

    tags_input = input("Tags (durch Kommas getrennt, optional): ")
    tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else None

    # Create the note
    result = await assigner.create_note_with_project(
        NOTES_DATABASE_ID,
        note_title,
        note_content,
        selected_project["id"],
        tags,
        note_source,
    )

    if isinstance(result, str):
        print(f"\nFehler beim Erstellen der Notiz: {result}")
    else:
        print(
            f"\nNotiz erfolgreich erstellt und mit Projekt '{selected_project['name']}' verknüpft!"
        )
        print(f"Notiz-URL: {result.get('url')}")


# Beispiel für eine programmatische Verwendung
async def programmatic_example():
    assigner = NotionProjectAssigner()

    # Database IDs
    NOTES_DATABASE_ID = "1a6389d5-7bd3-8097-aa38-e93cb052615a"  # Wissen & Notizen
    PROJECTS_DATABASE_ID = "1a6389d5-7bd3-80a3-a60e-cb6bc02f85d6"  # Projekte

    # Suche nach Projekten mit "Web" im Namen
    web_projects = await assigner.search_projects("Web", PROJECTS_DATABASE_ID)

    if not isinstance(web_projects, str) and web_projects:
        # Wähle das erste Projekt
        project = web_projects[0]

        # Erstelle eine neue Notiz und verknüpfe sie mit dem Projekt
        await assigner.create_note_with_project(
            NOTES_DATABASE_ID,
            "API-Dokumentation für Webprojekt",
            "Hier sind die wichtigsten Endpunkte für unsere API:\n\n- GET /users\n- POST /auth/login\n- PUT /users/{id}",
            project["id"],
            ["Programming", "API", "Dokumentation"],
            "Team Meeting vom 10.03.2025",
        )

        print(f"Notiz zum Projekt '{project['name']}' hinzugefügt.")
    else:
        print("Keine Web-Projekte gefunden.")


if __name__ == "__main__":
    # Interaktive Nutzung
    asyncio.run(interactive_assign_note_to_project())

    # Alternativ: Programmatische Nutzung
    # asyncio.run(programmatic_example())
