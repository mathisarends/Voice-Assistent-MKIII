"""
Haupteinstiegspunkt für den Sprachassistenten.
"""
import asyncio

from dotenv import load_dotenv

from assistant.conversation_loop import ConversationLoop
from assistant.speech_service import SpeechService
from audio.strategy.audio_manager import get_audio_manager
from audio.strategy.audio_strategies import AudioStrategyFactory
from graphs.workflow_registry import register_workflows

load_dotenv()

register_workflows()

get_audio_manager().set_strategy(AudioStrategyFactory.create_sonos_strategy())

async def main():
    speech_service = SpeechService(voice="nova")

    conversation = ConversationLoop(
        speech_service=speech_service,
        wakeword="picovoice",
        vocabulary=(
            "Wetterbericht, Abendroutine, Stopp, Licht an, "
            "Licht aus, Lautstärke, Pomodoro"
        ),
    )
    await conversation.run()


if __name__ == "__main__":
    asyncio.run(main())