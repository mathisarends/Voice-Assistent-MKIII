#!/usr/bin/env python3
"""
Haupteinstiegspunkt für den Sprachassistenten.
"""
import asyncio
from dotenv import load_dotenv

from assistant.audio_assistant import AudioAssistant
from assistant.conversation_loop import ConversationLoop
from graphs.workflow_registry import register_workflows

# Umgebungsvariablen laden
load_dotenv()

# Alle verfügbaren Workflows registrieren
register_workflows()

async def main():
    """Hauptfunktion zum Starten des Sprachassistenten."""
    assistant = AudioAssistant()
    conversation = ConversationLoop(
        assistant=assistant,
        wakeword="picovoice",
        vocabulary="Wetterbericht, Abendroutine, Stopp, Licht an, Licht aus, Licht dimmen, Licht heller"
    )
    
    await conversation.run()

if __name__ == "__main__":
    asyncio.run(main())