import os
import shutil
import threading
import queue
import uuid
from io import BytesIO
from typing import Optional

import pygame
from openai import OpenAI
from pydub import AudioSegment

from util.loggin_mixin import LoggingMixin


class SpeechService(LoggingMixin):
    def __init__(self, voice: str = "nova", cache_dir: str = "/tmp/tts_cache"):
        """
        Initialisiert den SpeechService mit OpenAI API und Audio-Framework.
        
        Args:
            voice: Die zu verwendende TTS-Stimme
            cache_dir: Verzeichnis zum Zwischenspeichern von TTS-Audiodateien
        """
        super().__init__()
        self.openai = OpenAI()
        self.voice = voice
        self.cache_dir = cache_dir
        
        # Sicherstellen, dass das Cache-Verzeichnis existiert
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialisierung der benötigten Komponenten
        self._setup_ffmpeg()
        self._setup_pygame()
        self._audio_lock = threading.Lock()
        
        # Queue-Mechanismen für die asynchrone Verarbeitung
        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()  
        
        # Worker-Threads für die TTS-Verarbeitung und Audiowiedergabe
        self.active = True
        self.tts_worker = threading.Thread(target=self._process_tts_queue, daemon=True)
        self.tts_worker.start()
        
        self.playback_worker = threading.Thread(target=self._process_audio_queue, daemon=True)
        self.playback_worker.start()
        
        self.logger.info("SpeechService initialisiert mit Stimme '%s'", voice)
    
    def _setup_ffmpeg(self) -> None:
        """Überprüft und setzt den FFmpeg-Pfad, falls nötig"""
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            self.logger.debug("FFmpeg gefunden: %s", ffmpeg_path)
        else:
            self.logger.warning("FFmpeg nicht gefunden! Versuche, Standard-Pfad zu setzen.")
            os.environ["PATH"] += os.pathsep + r"C:\ffmpeg-2025-02-17-git-b92577405b-essentials_build\bin"
            
    def _setup_pygame(self) -> None:
        """Initialisiert den pygame Mixer für die Audiowiedergabe"""
        try:
            pygame.mixer.quit()  
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            self.logger.debug("Pygame Mixer initialisiert")
        except Exception as e:
            self.logger.error("Pygame Initialisierungsfehler: %s", e)
    
    def _process_tts_queue(self) -> None:
        """Worker-Thread, der Texte in Audio umwandelt und zur Wiedergabe vorbereitet"""
        while self.active:
            try:
                text = self.text_queue.get(timeout=0.5)
                
                if not text.strip():
                    self.text_queue.task_done()
                    continue
                
                self.logger.debug("Generiere Sprache für: %s", text[:50] + ("..." if len(text) > 50 else ""))
                audio_data = self._generate_speech(text)
                
                if audio_data:
                    self.audio_queue.put((text, audio_data))
                
                self.text_queue.task_done()
                
            except queue.Empty:
                pass
            except Exception as e:
                self.logger.error("TTS-Verarbeitungsfehler: %s", e)
    
    def _process_audio_queue(self) -> None:
        """Worker-Thread, der vorbereitete Audiodateien abspielt"""
        while self.active:
            try:
                # Hole die nächste Audio-Datei aus der Queue
                text, audio_data = self.audio_queue.get(timeout=0.5)
                
                self.logger.debug("Spiele Audio ab für: %s", text[:50] + ("..." if len(text) > 50 else ""))
                # Spiele die Audio-Datei ab
                self._play_audio(audio_data)
                
                # Markiere Aufgabe als erledigt
                self.audio_queue.task_done()
                
            except queue.Empty:
                # Queue Timeout, setze Schleife fort
                pass
            except Exception as e:
                self.logger.error("Audio-Wiedergabefehler: %s", e)
    
    def _generate_speech(self, text: str) -> Optional[AudioSegment]:
        try:
            # Generiere eine eindeutige ID für diese Anfrage
            text_hash = str(uuid.uuid4())[:8]
            cache_path = os.path.join(self.cache_dir, f"tts_{text_hash}.mp3")
            
            # Generiere die Sprachdatei mit OpenAI
            response = self.openai.audio.speech.create(
                model="tts-1",
                voice=self.voice,
                input=text
            )
            
            # Speichere die MP3 im Cache
            with open(cache_path, "wb") as f:
                f.write(response.content)
            
            # Lade die MP3 direkt aus der API-Antwort
            audio_stream = BytesIO(response.content)
            audio = AudioSegment.from_file(audio_stream, format="mp3")
            
            return audio
            
        except Exception as e:
            self.logger.error("Fehler bei der Sprachgenerierung: %s", e)
            return None
    
    def _play_audio(self, audio_data: AudioSegment) -> None:
        with self._audio_lock:
            try:
                if not pygame.mixer.get_init():
                    self._setup_pygame()
                
                audio_io = BytesIO()
                audio_data.export(audio_io, format="wav")
                audio_io.seek(0)
                
                pygame.mixer.music.load(audio_io)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)
                    
            except Exception as e:
                self.logger.error("Wiedergabefehler: %s", e)
            finally:
                pygame.mixer.music.stop()
                audio_io.close()
            
    def interrupt_and_reset(self) -> bool:
        """
        Unterbricht die aktuelle Sprachausgabe und leert die Queues mit Deadlock-Vermeidung.
        
        Returns:
            bool: True, wenn erfolgreich zurückgesetzt
        """
        self.logger.debug("Unterbreche aktuelle Audioausgabe...")
        
        # Versuche Lock zu erwerben mit Timeout
        if self._audio_lock.acquire(timeout=1.0):
            try:
                # Stoppe Audioausgabe
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    try:
                        pygame.mixer.music.unload()
                    except:
                        pass
                
                # Leere Queues sicher
                self._clear_queues()
                
                self.logger.info("System bereit für neue Eingabe")
            finally:
                self._audio_lock.release()
        else:
            # Notfall-Reset bei Lock-Timeout
            self.logger.warning("Konnte Audio-Lock nicht erwerben, versuche alternative Stopstrategie")
            try:
                pygame.mixer.quit()
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                self.logger.info("Mixer wurde neu gestartet")
            except Exception as e:
                self.logger.error("Fehler beim Neustart des Mixers: %s", e)
        
        return True

    def _clear_queues(self) -> None:
        try:
            with self.text_queue.mutex:
                self.text_queue.queue.clear()
            with self.audio_queue.mutex:
                self.audio_queue.queue.clear()
        except Exception as e:
            self.logger.error("Fehler beim Leeren der Queues: %s", e)
    
    async def speak_response(self, response_text: str) -> str:
        """
        Spricht eine Antwort aus und gibt sie zurück.
        
        Args:
            response_text: Der auszusprechende Antworttext
            
        Returns:
            Der ausgesprochene Text
        """
        self.logger.info("🤖 Assistenten-Antwort: %s", response_text)
        
        if not response_text():
            return

        self.interrupt_and_reset()
        self.text_queue.put(response_text)
        self.logger.info("Text zur Sprachausgabe hinzugefügt: %s", response_text[:50] + ("..." if len(response_text) > 50 else ""))
        
        return response_text