from typing import Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

class YoutubeVideoSummarizer:
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.3):
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)
        
        self.summary_prompt = ChatPromptTemplate.from_template("""
        # Anleitung zur Zusammenfassung von YouTube-Videos
        
        Erstelle eine strukturierte Zusammenfassung im Markdown-Format für folgendes Video-Transkript:
        
        {transcript}
        
        ## Anforderungen an die Zusammenfassung:
        - Beginne mit einem prägnanten Titel (# Überschrift)
        - Füge direkt darunter den Link zum Video ein: {video_url}
        - Fasse die 5-7 wichtigsten Punkte des Videos in einer nummerierten Liste zusammen
        - Strukturiere die detaillierte Zusammenfassung in klare Abschnitte mit Überschriften (## Überschriften)
        - Verwende Aufzählungspunkte für wichtige Details
        - Behalte den Ton und Stil des Originalinhalts bei
        - Halte die Zusammenfassung prägnant (15-20% des Originaltranskripts)
        
        Die Zusammenfassung sollte direkt im Markdown-Format erfolgen, ohne zusätzliche Erklärungen.
        Wichtig: Das Format soll so sein:
        
        # [Prägnanter Titel]
        [Video-Link: {video_url}]
        
        ## Kernpunkte
        1. [Erster wichtiger Punkt]
        2. [Zweiter wichtiger Punkt]
        ...
        
        ## [Abschnittstitel 1]
        ...
        """)
        
        self.spoken_summary_prompt = ChatPromptTemplate.from_template("""
        # Anleitung für gesprochene Zusammenfassung
        
        Erstelle eine kurze, gesprochene Zusammenfassung der wichtigsten Punkte aus diesem Video aufgrundlage des dir gelieferten Transkripts.
        
        ## Anforderungen an die gesprochene Zusammenfassung:
        - Zu Beginn Youtbube-Video-Titel und Autor nennen falls vorhanden
        - Konversationell und natürlich klingen (wie in einem Gespräch)
        - Die 3-5 wichtigsten Erkenntnisse enthalten
        - Etwa 30-45 Sekunden lang sein, wenn sie gesprochen wird
        - In der zweiten Person formuliert sein ("Das Video behandelt...", "Der Autor erklärt...")
        - Beginne mit einem kurzen Satz zur Einleitung wie "Hier sind die wichtigsten Punkte aus dem Video..."
        
        ## Zusammenfassung des Videos, aus der du die wichtigsten Punkte extrahieren sollst:
        
        {summary}
        """)
        
    async def create_summary(self, transcript: str, video_title=None, video_url=None):
        if video_title:
            context = f"Titel des Videos: {video_title}\n\n{transcript}"
        else:
            context = transcript
        
        chain = self.summary_prompt | self.llm
        response = await chain.ainvoke({
            "transcript": context,
            "video_url": video_url or "[Kein Link verfügbar]"
        })
        
        return response.content
    
    async def create_spoken_summary(self, transcript: str, video_title: Optional[str] = None):
        if video_title:
            context = f"Titel des Videos: {video_title}\n\n{transcript}"
        else:
            context = transcript
        
        direct_spoken_prompt = ChatPromptTemplate.from_template("""
        # Anleitung für gesprochene Zusammenfassung
        
        Erstelle eine kurze, gesprochene Zusammenfassung der wichtigsten Punkte aus diesem Video-Transkript.
        
        ## Anforderungen an die gesprochene Zusammenfassung:
        - Konversationell und natürlich klingen (wie in einem Gespräch)
        - Die 3-5 wichtigsten Erkenntnisse enthalten
        - Etwa 30-45 Sekunden lang sein, wenn sie gesprochen wird
        - In der zweiten Person formuliert sein ("Das Video behandelt...", "Der Autor erklärt...")
        - Beginne mit einem kurzen Satz zur Einleitung wie "Hier sind die wichtigsten Punkte aus dem Video..."
        
        ## Video-Transkript:
        
        {transcript}
        """)
        
        chain = direct_spoken_prompt | self.llm
        response = await chain.ainvoke({
            "transcript": context
        })
        
        return response.content