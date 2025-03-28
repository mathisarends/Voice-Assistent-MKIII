from typing import Dict, Tuple, Optional, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
import json

from tools.google.youtube_client import YouTubeClient


class YoutubeFinder:
    def __init__(self, model_name: str = "gemini-2.0-flash", temperature: float = 0.2):
        self.youtube_client = YouTubeClient()

        # LLM initialisieren
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            top_p=0.95,
            top_k=40,
            streaming=False,
        )

        self.selection_prompt = ChatPromptTemplate.from_template(
            """
        # Anleitung zur Auswahl des besten YouTube-Videos
        
        ## Kontext:
        Du sollst aus den folgenden gelikten YouTube-Videos das beste Video auswählen, 
        das der Benutzeranfrage am besten entspricht.
        
        ## Gelikte Videos:
        {liked_videos}
        
        ## Wichtig zur Reihenfolge:
        Die Videos sind in chronologischer Reihenfolge aufgelistet, mit dem zuletzt gelikten Video an erster Stelle.
        Das erste Video in der Liste ist also das neueste/letzte gelikte Video.
        
        ## Benutzeranfrage:
        "{query}"
        
        ## Anforderungen:
        - Wähle das Video aus, das inhaltlich am besten zur Anfrage passt
        - Berücksichtige den Titel und den Kanal in deiner Entscheidung
        - Falls die Anfrage nach dem "letzten", "neuesten" oder "zuletzt gelikten" Video fragt, wähle das erste Video aus der Liste
        - Falls die Anfrage nach Videos von einem bestimmten Kanal fragt, berücksichtige dies besonders
        - Falls kein Video gut passt, gib das am passendsten zurück
        
        ## Format:
        Antworte ausschließlich im JSON-Format, ohne zusätzliche Erklärungen:
        {{
          "title": "Der vollständige Titel des ausgewählten Videos",
          "url": "Die vollständige YouTube-URL des Videos",
          "reason": "Ein kurzer Grund, warum dieses Video am besten passt"
        }}
        """
        )

    async def find_matching_video(
        self, query: str, max_results: int = 10
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Findet das beste passende Video aus den gelikten Videos basierend auf der Suchanfrage

        Args:
            query: Die Suchanfrage des Benutzers
            max_results: Maximale Anzahl der zu überprüfenden gelikten Videos

        Returns:
            Tuple mit (Titel, URL, Grund) des besten passenden Videos
        """
        # Gelikte Videos abrufen
        liked_videos = self.youtube_client.get_liked_videos(max_results=max_results)

        if not liked_videos:
            return None, None, "Keine gelikten Videos gefunden"

        # Anfrage an das LLM stellen
        chain = self.selection_prompt | self.llm
        response = await chain.ainvoke(
            {
                "liked_videos": json.dumps(liked_videos, indent=2, ensure_ascii=False),
                "query": query,
            }
        )

        try:
            # JSON-Antwort parsen
            result = json.loads(response.content)
            return result.get("title"), result.get("url")
        except (json.JSONDecodeError, AttributeError):
            # Fallback-Parsing, falls JSON nicht korrekt formatiert ist
            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            import re

            title_match = re.search(r'"title":\s*"([^"]+)"', content)
            url_match = re.search(r'"url":\s*"([^"]+)"', content)
            reason_match = re.search(r'"reason":\s*"([^"]+)"', content)

            title = title_match.group(1) if title_match else None
            url = url_match.group(1) if url_match else None

            return title, url


# Testlauf
if __name__ == "__main__":
    import asyncio

    async def main():
        finder = YoutubeFinder()
        title, url = await finder.find_matching_video("Thiago Forte Top Apps?")
        print(f"Gefundenes Video: {title}")
        print(f"URL: {url}")
        print(f"Grund: {reason}")

    asyncio.run(main())
