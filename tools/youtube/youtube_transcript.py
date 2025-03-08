# youtube_transcript.py
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter


class YoutubeTranscript:
    """Klasse zum Abrufen von Transkripten aus YouTube-Videos."""
    
    def get_transcript(self, url: str, format_text: bool = True):
        try:
            video_id = self._extract_video_id(url)
            
            if not video_id:
                return "Fehler: Ungültige YouTube-URL."
            
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            if format_text:
                formatter = TextFormatter()
                formatted_transcript = formatter.format_transcript(transcript_list)
                return formatted_transcript
            
            return transcript_list
            
        except Exception as e:
            return f"Fehler beim Abrufen des Transkripts: {str(e)}"
    
    def _extract_video_id(self, url: str) -> str:
        patterns = [
            r'(?:v=|\/videos\/|embed\/|youtu.be\/|\/v\/|\/e\/|watch\?v=|&v=)([^#\&\?\n<>\'\"]*)',
            r'(youtu\.be\/|youtube\.com\/(watch\?(.*&)?v=|(embed|v)\/))([^\?&"\'<> #]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1) if len(match.groups()) == 1 else match.group(5)
        
        return ""