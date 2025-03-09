# youtube_transcript.py
import re
from youtube_transcript_api import YouTubeTranscriptApi


class YoutubeTranscript:
    """Klasse zum Abrufen von Transkripten aus YouTube-Videos."""
    
    def get_transcript_by_url(self, url: str):
        try:
            video_id = self._extract_video_id(url)
            
            if not video_id:
                return {"transcript": "Fehler: Ungültige YouTube-Video-ID."}
            
            # Abrufen des Transkripts als Liste von Dictionaries
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Konvertieren in einen zusammenhängenden Text
            transcript_text = " ".join([entry.get('text', '') for entry in transcript_list])
            
            return transcript_text
                
        except Exception as e:
            return {"transcript": f"Fehler beim Abrufen des Transkripts: {str(e)}"}
    
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
    
    
if __name__ == "__main__":
    yt = YoutubeTranscript()
    url = "https://www.youtube.com/watch?v=NWfIrmIgaCU&t=7s&ab_channel=AliAbdaal"
    result = yt.get_transcript_by_url(url)
    print(result)