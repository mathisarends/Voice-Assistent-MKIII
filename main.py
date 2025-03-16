#!/usr/bin/env python3
"""
Haupteinstiegspunkt für den Sprachassistenten.
"""
import asyncio
from dotenv import load_dotenv

from assistant.speech_service import SpeechService
from assistant.conversation_loop import ConversationLoop
from graphs.workflow_registry import register_workflows

# Umgebungsvariablen laden
load_dotenv()

# Alle verfügbaren Workflows registrieren
register_workflows()

async def main():
    """Hauptfunktion zum Starten des Sprachassistenten."""
    speech_service = SpeechService()
    conversation = ConversationLoop(
        speech_service=speech_service,  # Hier muss eine SpeechService-Instanz übergeben werden
        wakeword="picovoice",
        vocabulary="Wetterbericht, Abendroutine, Stopp, Licht an, Licht aus, Lautstärke"
    )
    await conversation.run()

if __name__ == "__main__":
    asyncio.run(main())