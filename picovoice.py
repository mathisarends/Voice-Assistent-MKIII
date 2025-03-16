import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from graphs.workflows.notion_todo_workflow import NotionTodoWorkflow
from graphs.workflows.research_workflow import ResearchWorkflow
from graphs.workflows.spotify_workflow import SpotifyWorkflow
from graphs.workflows.weather_workflow import WeatherWorkflow
from speech.voice_generator import VoiceGenerator
from graphs.workflow_dispatcher import WorkflowDispatcher
from graphs.workflow_registry import WorkflowRegistry
from graphs.workflows.alarm_workflow import AlarmWorkflow
from graphs.workflows.lights_workflow import LightsWorkflow
from speech.wake_word_listener import WakeWordListener
from speech.recognition.whisper_speech_recognition import WhisperSpeechRecognition
from speech.recognition.audio_transcriber import AudioTranscriber
from tools.time.time_tool import TimeTool
from util.loggin_mixin import LoggingMixin
from audio.audio_manager import play

voice_generator = VoiceGenerator()

load_dotenv()

def register_workflows():
    """Registriert alle verfügbaren Workflows in der Registry."""
    WorkflowRegistry.register(
        "lights",
        LightsWorkflow,
        "Steuert Philips Hue Beleuchtung mit Szenen, Helligkeit und Ein-/Ausschalt-Funktionen",
        ["Beleuchtung", "Philips Hue", "Szenen", "Helligkeit"]
    )
    
    WorkflowRegistry.register(
        "alarm",
        AlarmWorkflow,
        "Verwaltet Alarme mit Wake-Up und Get-Up Phasen sowie Lichtwecker-Integration",
        ["Alarm", "Wecker", "Aufwachen", "Lichtwecker", "Timer"]
    )
    
    WorkflowRegistry.register(
        "weather",
        WeatherWorkflow,
        "Liefert aktuelle Wetterinformationen und bereitet sie für Sprachwiedergabe auf",
        ["Wetter", "Vorhersage", "Sprachsteuerung", "Temperatur", "Regen"]
    )
    
    WorkflowRegistry.register(
        "time",
        TimeTool,
        "Gibt das aktuelle Datum und die Uhrzeit für Sprachsteuerung oder Automationen zurück",
        ["Zeit", "Datum", "Uhrzeit"]
    )
    
    WorkflowRegistry.register(
        "spotify",
        SpotifyWorkflow,
        "Steuert Spotify-Wiedergabe, Lautstärke, Geräte und Playlists per Sprachbefehl",
        ["Musik", "Spotify", "Wiedergabe", "Playlist", "Lautstärke", "Geräte"]
    )
    
    WorkflowRegistry.register(
        "notion_todo",
        NotionTodoWorkflow,
        "Verwaltet Notion-Tasks, Projekte und tägliche Top-Aufgaben für Produktivität",
        ["Notion", "To-Do", "Projektmanagement", "Produktivität", "Tägliche Aufgaben"]
    )
    
    WorkflowRegistry.register(
        "notion_clipboard",
        ResearchWorkflow,
        "Durchsucht das Web nach relevanten Informationen und speichert sie in der Notion zwischenablage",
        ["Recherche", "Websuche", "Notion", "Zwischenablage"]
    )
    
    
    
register_workflows()
    
workflow_dispatcher = WorkflowDispatcher()

class AudioAssistant(LoggingMixin):
    """Einfache Klasse für Sprachassistenten-Logik ohne externe APIs"""
    
    async def process_and_respond(self, user_text):
        """Verarbeitet Benutzereingabe und gibt eine Antwort zurück"""
        self.logger.info("Verarbeite Anfrage: %s", user_text)
        
        voice_generator.speak(user_text)
        self.logger.info("Antwort: %s", user_text)
        return user_text

    async def speak_response(self, user_text):
        """Generiert eine Antwort und würde sie aussprechen"""
        response = await self.process_and_respond(user_text)

        print(f"🤖 Assistenten-Antwort: {response}")
        return response
    

class ConversationLoop(LoggingMixin):
    """Verwaltet den Haupt-Konversationsloop des Sprachassistenten"""
    
    def __init__(self, 
                 assistant: VoiceGenerator,
                 wakeword: str = "picovoice",
                 vocabulary: str = "Wetterbericht, Abendroutine, Stopp"):
        """
        Initialisiert den Konversationsloop.
        
        Args:
            assistant: Der zu verwendende Sprachassistent (muss speak_response implementieren)
            wakeword: Das zu verwendende Wake-Word
            vocabulary: Spezielle Vokabeln zur Verbesserung der Spracherkennung
        """
        super().__init__()
        self.wakeword = wakeword
        self.vocabulary = vocabulary
        self.assistant = assistant
        self.speech_recorder = WhisperSpeechRecognition()
        self.audio_transcriber = AudioTranscriber()
        self.should_stop = False
    
    @asynccontextmanager
    async def create_wakeword_listener(self):
        """Erstellt einen WakeWordListener als async context manager"""
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
        
        play("process-sound-new")
        self.logger.info("🗣 Erkannt: %s", user_prompt)
        

        result = workflow_dispatcher.dispatch(user_prompt)
        selected_workflow = result["workflow"]
        print(f"Ausgewählter Workflow: {selected_workflow}")
        
        result = await workflow_dispatcher.run_workflow(selected_workflow, user_prompt, f"demo")
        
        await self.assistant.speak_response(result)
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
                            voice_generator.interrupt_and_reset()
                            audio_data = self.speech_recorder.record_audio()
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


# Beispielnutzung:
async def main():
    
    assistant = AudioAssistant()
    conversation = ConversationLoop(
        assistant=assistant,
        wakeword="picovoice",
        vocabulary="Wetterbericht, Abendroutine, Stopp, Licht an, Licht aus, Licht dimmen, Licht heller"
    )
    
    await conversation.run()

if __name__ == "__main__":
    asyncio.run(main())