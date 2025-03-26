#!/usr/bin/env python3
"""
Haupteinstiegspunkt für den Sprachassistenten.
"""
import asyncio
from dotenv import load_dotenv

from assistant.speech_service import SpeechService
from assistant.conversation_loop import ConversationLoop
from graphs.workflow_registry import register_workflows
from audio.sonos.sonos_setup import setup_sonos

# Umgebungsvariablen laden
load_dotenv()

# Alle verfügbaren Workflows registrieren
register_workflows()

setup_sonos()

async def main():
    speech_service = SpeechService(voice="nova")
    
    conversation = ConversationLoop(
        speech_service=speech_service,
        wakeword="picovoice",
        vocabulary="Wetterbericht, Abendroutine, Stopp, Licht an, Licht aus, Lautstärke, Pomodoro"
    )
    await conversation.run()

if __name__ == "__main__":
    asyncio.run(main())