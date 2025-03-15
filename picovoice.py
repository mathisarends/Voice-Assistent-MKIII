import asyncio
import logging
from contextlib import asynccontextmanager

from speech.wake_word_listener import WakeWordListener
from speech.recognition.speech_recorder import SpeechRecorder
from speech.recognition.audio_transcriber import AudioTranscriber
from audio.audio_manager import play

from dotenv import load_dotenv
load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("assistant")

class AudioAssistant:
    """Einfache Klasse für Sprachassistenten-Logik ohne externe APIs"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Initialisiere Audio-Assistenten")
        
    async def process_and_respond(self, user_text):
        """Verarbeitet Benutzereingabe und gibt eine Antwort zurück"""
        self.logger.info("Verarbeite Anfrage: %s", user_text)
        
        # Hier könnte später die Integration mit einem echten Chat-Assistenten erfolgen
        # Aktuell einfache Echo-Antwort
        response = f"Sie sagten: {user_text}"
        
        self.logger.info("Antwort: %s", response)
        return response
        
    async def speak_response(self, user_text):
        """Generiert eine Antwort und würde sie aussprechen"""
        response = await self.process_and_respond(user_text)
        
        print(f"🤖 Assistenten-Antwort: {response}")
        return response

@asynccontextmanager
async def create_wakeword_listener(wakeword="computer"):
    """Erstellt einen WakeWordListener als async context manager"""
    listener = WakeWordListener(wakeword=wakeword)
    try:
        yield listener
    finally:
        listener.cleanup()
        
async def main():
    speech_recorder = SpeechRecorder()
    audio_transcriber = AudioTranscriber()
    assistant = AudioAssistant()
    
    logger.info("🚀 Starte den Sprachassistenten")
    
    async with create_wakeword_listener(wakeword="picovoice") as wakeword_listener:
        try:
            logger.info("🎤 Warte auf Wake-Word...")
            
            # Hauptschleife
            while True:
                # Auf Wake-Word warten
                if wakeword_listener.listen_for_wakeword():
                    logger.info("🔔 Wake-Word erkannt, starte Sprachaufnahme")
                    
                    try:
                        audio_data = speech_recorder.record_audio()
                        
                        user_prompt = await audio_transcriber.transcribe_audio(audio_data, vocabulary="Wetterbericht, Abendroutine, Stopp")
                        
                        if not user_prompt or user_prompt.strip() == "":
                            play("stop-listening-no-message")
                            logger.info("⚠️ Keine Sprache erkannt oder leerer Text")
                            continue
                        
                        play("stop-listening")
                        logger.info("🗣 Erkannt: %s", user_prompt)
                        
                        await assistant.speak_response(user_prompt)
                            
                    except Exception as e:
                        logger.error("Fehler bei der Sprachverarbeitung: %s", e)
                        
        except KeyboardInterrupt:
            logger.info("🛑 Programm manuell beendet.")
            
        except Exception as e:
            logger.error("❌ Unerwarteter Fehler: %s", e)

if __name__ == "__main__":
    asyncio.run(main())