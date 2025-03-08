# youtube_finder.py
import re
from typing import Dict, Optional
from langchain_openai import ChatOpenAI
from browser_use import Agent


class YoutubeFinder:
    """Findet YouTube-Videos basierend auf einer Beschreibung und gibt Titel und URL zurück."""
    
    async def find_video(self, prompt: str) -> Dict:

        try:
            result = await self._find_youtube_video(prompt)
            
            if result.get('url'):
                return {
                    "title": result.get('title'),
                    "url": result.get('url'),
                    "success": True
                }
            else:
                return {
                    "success": False,
                    "error_message": "Kein passendes YouTube-Video gefunden."
                }
        
        except Exception as e:
            return {
                "success": False,
                "error_message": f"Fehler bei der Verarbeitung: {str(e)}"
            }
    
    def _extract_url(self, text: str) -> Optional[str]:

        url_match = re.search(r'https://www\.youtube\.com/watch\?v=[a-zA-Z0-9_-]+', text)
        return url_match.group(0) if url_match else None
    
    def _extract_title(self, text: str, url: Optional[str] = None) -> Optional[str]:
        title_match = re.search(r'(?:Titel|Title):\s*([^\n]+)', text)
        if title_match:
            return title_match.group(1).strip()
        
        if url:
            text_without_url = text.replace(url, "").strip()
            lines = text_without_url.split('\n')
            if lines and len(lines[0]) < 200:
                return lines[0].strip()
        
        return None
    
    async def _find_youtube_video(self, prompt: str) -> Dict[str, Optional[str]]:
        enhanced_prompt = (
            f"Finde das beste YouTube-Video, das folgender Beschreibung entspricht: '{prompt}'. "
            "Gib sowohl die vollständige YouTube-URL als auch den exakten Titel des Videos zurück. "
            "Formatiere deine Antwort so: 'Titel: [VIDEOTITEL]\\nURL: [VIDEOURL]'"
        )
        
        agent = Agent(
            task=enhanced_prompt,
            llm=ChatOpenAI(model="gpt-4o-mini"),
            use_vision=False
        )
        
        result = await agent.run()
        final_text = result.final_result()
        
        if not final_text:
            return {"url": None, "title": None}
        
        url = self._extract_url(final_text)
        title = self._extract_title(final_text, url)
        
        return {"url": url, "title": title}