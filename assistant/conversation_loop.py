from contextlib import asynccontextmanager

from assistant.speech_service import SpeechService
from audio.audio_manager import play
from graphs.workflow_dispatcher import WorkflowDispatcher
from speech.recognition.whisper_speech_recognition import WhisperSpeechRecognition
from speech.recognition.audio_transcriber import AudioTranscriber
from speech.wake_word_listener import WakeWordListener
from util.loggin_mixin import LoggingMixin

class ConversationLoop(LoggingMixin):
    def __init__(self, 
                 speech_service: SpeechService,
                 wakeword="picovoice",
                 vocabulary="Wetterbericht, Abendroutine, Stopp"):
        super().__init__()
        self.wakeword = wakeword
        self.vocabulary = vocabulary
        self.speech_service = speech_service
        self.speech_recorder = WhisperSpeechRecognition()
        self.audio_transcriber = AudioTranscriber()
        self.workflow_dispatcher = WorkflowDispatcher()
        self.should_stop = False
    
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
    
    async def handle_user_input(self, audio_data):
        """Verarbeitet die Audio-Eingabe des Benutzers und gibt die Antwort aus."""
        user_prompt = await self.audio_transcriber.transcribe_audio(
            audio_data, 
            vocabulary=self.vocabulary
        )
        
        if not user_prompt or user_prompt.strip() == "":
            play("stop-listening-no-message")
            self.logger.info("⚠️ Keine Sprache erkannt oder leerer Text")
            return False
        
        self.logger.info("🗣 Erkannt: %s", user_prompt)
        
        result = await self.workflow_dispatcher.dispatch(user_prompt)
        selected_workflow = result["workflow"]
        self.logger.info("Ausgewählter Workflow '%s'", selected_workflow)
        
        result = await self.workflow_dispatcher.run_workflow(selected_workflow, user_prompt, "demo")
        await self.speech_service.speak_response(result)
        
        return True
    
    async def run(self):
        """Startet den Haupt-Konversationsloop."""
        self.logger.info("🚀 Starte den Sprachassistenten mit Wake-Word '%s'", self.wakeword)
        
        async with self.create_wakeword_listener() as wakeword_listener:
            self.logger.info("🎤 Warte auf Wake-Word...")
            
            # Hauptschleife
            while not self.should_stop:
                try:
                    # Auf Wake-Word warten
                    if wakeword_listener.listen_for_wakeword():
                        self.logger.info("🔔 Wake-Word erkannt, starte Sprachaufnahme")
                        
                        try:
                            self.speech_service.interrupt_and_reset()
                            audio_data = self.speech_recorder.record_audio()
                            play("process-sound-new")
                            
                            await self.handle_user_input(audio_data)
                                
                        except Exception as e:
                            self.logger.error("Fehler bei der Sprachverarbeitung: %s", e)
                            
                except KeyboardInterrupt:
                    self.logger.info("🛑 Programm manuell beendet.")
                    self.should_stop = True
                    
                except Exception as e:
                    self.logger.error("❌ Unerwarteter Fehler: %s", e)
    
    def stop(self):
        """Stoppt den Konversationsloop."""
        self.should_stop = True
        self.logger.info("Konversationsloop wird gestoppt...")