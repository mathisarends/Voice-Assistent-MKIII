import asyncio
import re
from tools.notion.core.abstract_notion_client import AbstractNotionClient

class NotionNLPAssistant(AbstractNotionClient):
    """A Notion assistant that understands natural language to add information to projects."""
    
    def __init__(self):
        super().__init__()
        self.notes_database_id = "1a6389d5-7bd3-8097-aa38-e93cb052615a"  # Wissen & Notizen
        self.projects_database_id = "1a6389d5-7bd3-80a3-a60e-cb6bc02f85d6"  # Projekte
        self.second_brain_id = "1a6389d5-7bd3-80c5-9a87-e90b034989d0"  # Second Brain
        
    async def process_natural_language_request(self, user_request):
        """Process a natural language request to add information to a project."""
        # Step 1: Parse the user request
        parsed_request = self._parse_user_request(user_request)
        
        if not parsed_request.get("project_hint"):
            return {
                "success": False,
                "message": "Ich konnte keinen Projektnamen in Ihrer Anfrage erkennen. Bitte erwähnen Sie ein Projekt explizit."
            }
            
        # Step 2: Find matching projects
        matching_projects = await self._find_matching_projects(parsed_request["project_hint"])
        
        if not matching_projects:
            return {
                "success": False,
                "message": f"Kein Projekt gefunden, das '{parsed_request['project_hint']}' enthält. Bitte überprüfen Sie den Projektnamen."
            }
            
        # Step 3: Select best matching project
        selected_project = self._select_best_project(matching_projects, parsed_request["project_hint"])
        
        # Step 4: Create the note with information
        note_result = await self._create_note_for_project(
            selected_project["id"],
            parsed_request["title"],
            parsed_request["content"],
            parsed_request.get("tags", []),
            parsed_request.get("source")
        )
        
        if isinstance(note_result, str):  # Error case
            return {
                "success": False,
                "message": f"Fehler beim Erstellen der Notiz: {note_result}"
            }
            
        return {
            "success": True,
            "message": f"Informationen zu '{parsed_request['title']}' wurden im Projekt '{selected_project['name']}' gespeichert.",
            "note_url": note_result.get("url"),
            "project": selected_project["name"]
        }
        
    def _parse_user_request(self, user_request):
        """Parse the user's natural language request to extract key information."""
        result = {
            "original_request": user_request,
            "project_hint": None,
            "title": None,
            "content": "",
            "tags": [],
            "source": None
        }
        
        # Extract project name (look for patterns like "im Projekt X", "zum Projekt X", "in X")
        project_patterns = [
            r"(?:im|zum|für|in|unter|zu)\s+(?:projekt|projekte|project)?\s*[\"']?([^\"'.!?]+)[\"']?",
            r"(?:projekt|projekte|project)\s+[\"']?([^\"'.!?]+)[\"']?"
        ]
        
        for pattern in project_patterns:
            project_match = re.search(pattern, user_request, re.IGNORECASE)
            if project_match:
                result["project_hint"] = project_match.group(1).strip()
                break
                
        # Extract title (main topic/subject of the information)
        # First, look for explicit title indicators
        title_match = re.search(r"(?:informationen|notiz|eintrag|info)\s+(?:zu|über|für|about)\s+[\"']?([^\"'.!?]+)[\"']?", user_request, re.IGNORECASE)
        
        if title_match:
            result["title"] = title_match.group(1).strip()
        else:
            # If no explicit title indicator, try to extract the main subject
            # This is a simplified approach - in a real system, you might use NLP techniques
            words = user_request.split()
            # Look for the first noun phrase after verbs like "schreibe", "notiere", etc.
            verb_indices = [i for i, word in enumerate(words) if word.lower() in ["schreibe", "notiere", "speichere", "erstelle"]]
            
            if verb_indices:
                # Take words after the first action verb until a preposition or end of sentence
                start_idx = verb_indices[0] + 1
                end_idx = len(words)
                for i in range(start_idx, len(words)):
                    if words[i].lower() in ["im", "in", "zum", "für", "unter", "zu"]:
                        end_idx = i
                        break
                        
                if start_idx < end_idx:
                    result["title"] = " ".join(words[start_idx:end_idx])
            
            # If we still don't have a title, use a generic one
            if not result["title"]:
                result["title"] = f"Notiz zu {result['project_hint']}" if result["project_hint"] else "Neue Notiz"
        
        # Extract content (any detailed information provided)
        content_match = re.search(r"(?:mit\s+(?:inhalt|content))\s*:?\s*[\"']?([^\"']+)[\"']?", user_request, re.IGNORECASE)
        if content_match:
            result["content"] = content_match.group(1).strip()
            
        # Extract tags (if mentioned)
        tags_match = re.search(r"(?:tags|schlagworte|schlagwörter|kategorien)\s*:?\s*[\"']?([^\"']+)[\"']?", user_request, re.IGNORECASE)
        if tags_match:
            tag_text = tags_match.group(1)
            # Split by common separators
            result["tags"] = [tag.strip() for tag in re.split(r"[,;/|]", tag_text)]
            
        # Extract source (if mentioned)
        source_match = re.search(r"(?:quelle|source|von|from|link)\s*:?\s*[\"']?([^\"']+)[\"']?", user_request, re.IGNORECASE)
        if source_match:
            result["source"] = source_match.group(1).strip()
            
        return result
        
    async def _find_matching_projects(self, project_hint):
        """Find projects that match the given hint."""
        # Get all projects
        response = await self._make_request(
            "post",
            "databases/" + self.projects_database_id + "/query",
            {}
        )
        
        if response.status_code != 200:
            self.logger.error(f"Error retrieving projects: {response.text}")
            return []
            
        projects = response.json().get("results", [])
        
        # Filter projects by the hint
        matching_projects = []
        for project in projects:
            project_name = self._extract_page_title(project)
            if project_hint.lower() in project_name.lower():
                matching_projects.append({
                    "id": project["id"],
                    "name": project_name,
                    "similarity": self._calculate_similarity(project_name, project_hint)
                })
                
        # Sort by similarity score (highest first)
        matching_projects.sort(key=lambda p: p["similarity"], reverse=True)
        return matching_projects
        
    def _calculate_similarity(self, project_name, project_hint):
        """Calculate a simple similarity score between project name and hint."""
        # This is a very simple implementation
        # For better results, consider using proper string similarity algorithms
        
        # Convert both to lowercase for comparison
        name_lower = project_name.lower()
        hint_lower = project_hint.lower()
        
        # Exact match gets highest score
        if name_lower == hint_lower:
            return 1.0
            
        # Contains the full hint as a substring
        if hint_lower in name_lower:
            return 0.8
            
        # Check for word overlap
        name_words = set(name_lower.split())
        hint_words = set(hint_lower.split())
        common_words = name_words.intersection(hint_words)
        
        if common_words:
            return 0.5 * len(common_words) / len(hint_words)
            
        # No strong match
        return 0.0
        
    def _select_best_project(self, matching_projects, project_hint):
        """Select the best matching project based on similarity."""
        if not matching_projects:
            return None
            
        # For now, simply return the first (highest similarity) match
        return matching_projects[0]
        
    async def _create_note_for_project(self, project_id, title, content, tags=None, source=None):
        """Create a new note linked to the specified project."""
        # Prepare properties
        properties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "📁 Projekte": {
                "relation": [
                    {
                        "id": project_id
                    }
                ]
            }
        }
        
        # Add tags if provided
        if tags and isinstance(tags, list):
            properties["Tags"] = {
                "multi_select": [{"name": tag} for tag in tags]
            }
            
        # Add source if provided
        if source:
            properties["Quelle"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": source
                        }
                    }
                ]
            }
            
        # Set status to "Entwurf" (Draft)
        properties["Status"] = {
            "status": {
                "name": "Entwurf"
            }
        }
        
        # Prepare the request body
        request_body = {
            "parent": {
                "database_id": self.notes_database_id
            },
            "properties": properties
        }
        
        # Add content if provided
        if content:
            request_body["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": content
                                }
                            }
                        ]
                    }
                }
            ]
        
        # Make the request to create the page
        response = await self._make_request("post", "pages", request_body)
        
        if response.status_code != 200:
            self.logger.error(f"Error creating note: {response.text}")
            return f"Error creating note: {response.text}"
            
        return response.json()
        
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


async def handle_voice_command(command):
    """Handle a voice command for the notion assistant."""
    assistant = NotionNLPAssistant()
    result = await assistant.process_natural_language_request(command)
    
    if result["success"]:
        return result["message"]
    else:
        return result["message"]


# Example usage
async def main():
    # Example commands to test the NLP capabilities
    test_commands = [
        "Schreibe Informationen zu Browser-Use Framework in mein Second Brain im Projekt Jarvis",
        "Erstelle eine Notiz über Machine Learning Algorithmen im Projekt AI Research mit Tags: KI, Python, Daten",
        "Speichere die Links zum neuen Design in Projekt Website Redesign, Quelle: Team Meeting",

    ]
    
    for command in test_commands:
        print(f"\nBefehl: {command}")
        response = await handle_voice_command(command)
        print(f"Antwort: {response}")


if __name__ == "__main__":
    asyncio.run(main())