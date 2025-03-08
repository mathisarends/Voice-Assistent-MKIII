from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

class YoutubeVideoSummarizer:

    
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.3):

        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)
        self.prompt = ChatPromptTemplate.from_template("""
        # Anleitung zur Zusammenfassung von YouTube-Videos
        
        Erstelle eine strukturierte Zusammenfassung im Markdown-Format für folgendes Video-Transkript:
        
        {transcript}
        
        ## Anforderungen an die Zusammenfassung:
        - Beginne mit einem prägnanten Titel (# Überschrift)
        - Fasse die 5-7 wichtigsten Punkte des Videos in einer nummerierten Liste zusammen
        - Strukturiere die detaillierte Zusammenfassung in klare Abschnitte mit Überschriften (## Überschriften)
        - Verwende Aufzählungspunkte für wichtige Details
        - Behalte den Ton und Stil des Originalinhalts bei
        - Halte die Zusammenfassung prägnant (15-20% des Originaltranskripts)
        
        Die Zusammenfassung sollte direkt im Markdown-Format erfolgen, ohne zusätzliche Erklärungen.
        """)
    
    async def create_summary(self, transcript: str, video_title=None):
        cleaned_transcript = " ".join(transcript.split())
        
        if video_title:
            context = f"Titel des Videos: {video_title}\n\n{cleaned_transcript}"
        else:
            context = cleaned_transcript
        
        chain = self.prompt | self.llm
        response = await chain.ainvoke({"transcript": context})
        
        return response.content