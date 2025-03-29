import asyncio
import traceback
from contextlib import asynccontextmanager

from assistant.speech_service import SpeechService
from assistant.state import WaitingForWakeWordState
from audio.strategy.audio_manager import get_audio_manager
from graphs.workflow_dispatcher import WorkflowDispatcher
from graphs.workflow_registry import register_workflows
from speech.recognition.audio_transcriber import AudioTranscriber
from speech.recognition.whisper_speech_recognition import \
    WhisperSpeechRecognition
from speech.wake_word_listener import WakeWordListener
from util.loggin_mixin import LoggingMixin

register_workflows()

class ConversationStateMachine(LoggingMixin):
    def __init__(
        self,
        speech_service: SpeechService,
        wakeword="picovoice",
        vocabulary="Wetterbericht, Abendroutine, Stopp Wetter",
    ):
        super().__init__()
        self.wakeword = wakeword
        self.vocabulary = vocabulary
        self.speech_service = speech_service
        self.speech_recorder = WhisperSpeechRecognition()
        self.audio_transcriber = AudioTranscriber()
        self.workflow_dispatcher = WorkflowDispatcher()
        self.audio_manager = get_audio_manager()
        self.should_stop = False
        
        self.current_state = None
        self.wakeword_listener = None

    @asynccontextmanager
    async def create_wakeword_listener(self):
        """
        Erstellt einen WakeWordListener als async context manager.

        Yields:
            WakeWordListener: Der initialisierte WakeWordListener.
        """
        listener = WakeWordListener(wakeword=self.wakeword)
        try:
            yield listener
        finally:
            listener.cleanup()

    async def run(self):
        """Startet die Zustandsmaschine"""
        self.logger.info(
            "🚀 Starte den Sprachassistenten mit Wake-Word '%s'", self.wakeword
        )

        async with self.create_wakeword_listener() as wakeword_listener:
            self.wakeword_listener = wakeword_listener
            
            # Setze den initialen Zustand
            self.current_state = WaitingForWakeWordState(
                wakeword_listener=wakeword_listener,
                speech_service=self.speech_service,
                speech_recorder=self.speech_recorder
            )
            
            # Starte die Zustandsmaschine
            await self._run_state_machine()

    async def _run_state_machine(self):
        """Interne Methode zum Ausführen der Zustandsmaschine"""
        initial_state_type = type(self.current_state)
        
        while not self.should_stop:
            try:
                # Verarbeite den aktuellen Zustand
                next_state = await self.current_state.process()
                
                if next_state is None:
                    # Spezialfall: Zurück zum Anfangszustand
                    self.current_state = WaitingForWakeWordState(
                        wakeword_listener=self.wakeword_listener,
                        speech_service=self.speech_service,
                        speech_recorder=self.speech_recorder
                    )
                else:
                    # Wechsel zum nächsten Zustand
                    self.current_state = next_state
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Programm manuell beendet.")
                self.should_stop = True
                
            except Exception as e:
                self.logger.error("❌ Unerwarteter Fehler in der Zustandsmaschine: %s", e)
                self.logger.error("Traceback: %s", traceback.format_exc())
                
                # Bei einem unerwarteten Fehler zurück zum Anfangszustand
                self.current_state = WaitingForWakeWordState(
                    wakeword_listener=self.wakeword_listener,
                    speech_service=self.speech_service,
                    speech_recorder=self.speech_recorder
                )

    def stop(self):
        """Stoppt die Zustandsmaschine"""
        self.should_stop = True
        self.logger.info("Zustandsmaschine wird gestoppt...")


# Beispiel für die Verwendung
async def main():
    speech_service = SpeechService()
    
    # Erstelle die Zustandsmaschine statt des ConversationLoop
    state_machine = ConversationStateMachine(
        speech_service=speech_service,
        wakeword="picovoice",
    )
    
    try:
        # Starte die Zustandsmaschine
        await state_machine.run()
    except KeyboardInterrupt:
        print("Beende das Programm...")
    finally:
        state_machine.stop()


if __name__ == "__main__":
    asyncio.run(main())