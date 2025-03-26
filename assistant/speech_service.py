import os
import shutil
import threading
import queue
import time
import hashlib
from io import BytesIO
from typing import Optional, Tuple

import pygame
from openai import OpenAI
from pydub import AudioSegment

from audio.sonos.sonos_manager import SonosAudioManager
from util.loggin_mixin import LoggingMixin
from singleton_decorator import singleton

@singleton
class SpeechService(LoggingMixin):
    def __init__(self, voice: str = "nova", cache_dir: str = "./audio/sounds/temp_responses", use_sonos: bool = True, cache_cleanup_interval: int = 120):
        """
        Initialisiert den SpeechService mit OpenAI API und Audio-Framework.
        
        Args:
            voice: Die zu verwendende TTS-Stimme
            cache_dir: Verzeichnis zum Zwischenspeichern von TTS-Audiodateien
            use_sonos: Wenn True, wird Sonos für die Audiowiedergabe verwendet
            cache_cleanup_interval: Intervall in Sekunden für das Löschen alter Cache-Dateien
        """
        super().__init__()
        self.openai = OpenAI()
        self.voice = voice
        
        # Projektpfad finden (relativ)
        self.project_dir = os.path.abspath(os.path.curdir)
        self.cache_dir = os.path.join(self.project_dir, cache_dir)
        self.use_sonos = use_sonos
        self.cache_cleanup_interval = cache_cleanup_interval
        self._last_cleanup_time = time.time()
        
        # Sicherstellen, dass das Cache-Verzeichnis existiert
        os.makedirs(self.cache_dir, exist_ok=True)
        self.logger.info(f"TTS Cache-Verzeichnis: {self.cache_dir}")
        
        # Initialisierung der benötigten Komponenten
        self._setup_ffmpeg()
        
        # Sonos Manager referenzieren (als Singleton bereits initialisiert)
        self.sonos_manager = SonosAudioManager() if use_sonos else None
        
        # Pygame nur initialisieren, wenn kein Sonos verwendet wird oder als Fallback
        if not use_sonos or not self.sonos_manager.sonos_device:
            self._setup_pygame()
            if use_sonos:
                self.logger.warning("Kein Sonos-Gerät verfügbar, verwende lokale Wiedergabe")
                self.use_sonos = False
        else:
            self.logger.info("Sonos-Integration aktiviert mit Gerät: %s", 
                            self.sonos_manager.sonos_device.player_name)
            
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
                result = self._generate_speech(text)
                
                if result:
                    audio_data, cache_path = result
                    self.audio_queue.put((text, audio_data, cache_path))
                
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
                text, audio_data, cache_path = self.audio_queue.get(timeout=0.5)
                
                self.logger.debug("Spiele Audio ab für: %s", text[:50] + ("..." if len(text) > 50 else ""))
                
                # Spiele die Audio-Datei ab
                self._play_audio(audio_data, cache_path)
                
                # Markiere Aufgabe als erledigt
                self.audio_queue.task_done()
                
            except queue.Empty:
                # Queue Timeout, setze Schleife fort
                pass
            except Exception as e:
                self.logger.error("Audio-Wiedergabefehler: %s", e)
    
    def _get_text_hash(self, text: str) -> str:
        """
        Erzeugt einen konsistenten Hash für einen Text.
        
        Args:
            text: Der zu hashende Text
            
        Returns:
            str: Ein MD5-Hash (gekürzt auf 8 Zeichen)
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]
    
    def _clean_old_cache_files(self):
        """
        Löscht alte Cache-Dateien, die älter als das Cleanup-Intervall sind.
        """
        current_time = time.time()
        
        # Überprüfen, ob ein Cleanup nötig ist
        if current_time - self._last_cleanup_time < self.cache_cleanup_interval:
            return
            
        self.logger.info("🧹 Räume alte TTS-Cache-Dateien auf...")
        cleanup_time = current_time - self.cache_cleanup_interval
        
        try:
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith('.mp3'):
                    continue
                    
                file_path = os.path.join(self.cache_dir, filename)
                file_mod_time = os.path.getmtime(file_path)
                
                if file_mod_time < cleanup_time:
                    os.remove(file_path)
                    self.logger.debug(f"Gelöschte Cache-Datei: {filename}")
                    
                    # Entferne auch aus dem Sonos-Manager, falls vorhanden
                    sound_id = os.path.splitext(filename)[0]
                    if self.use_sonos and self.sonos_manager and sound_id in self.sonos_manager.sound_map:
                        del self.sonos_manager.sound_map[sound_id]
            
            self._last_cleanup_time = current_time
            self.logger.info("🧹 Cache-Bereinigung abgeschlossen")
            
        except Exception as e:
            self.logger.error(f"Fehler bei der Cache-Bereinigung: {e}")
    
    def _register_with_sonos_manager(self, sound_id: str, file_path: str):
        """
        Registriert eine Audio-Datei beim Sonos-Manager, damit sie abspielbar ist.
        
        Args:
            sound_id: Die Sound-ID (Dateiname ohne Erweiterung)
            file_path: Der vollständige Pfad zur Audio-Datei
        """
        try:
            if not self.sonos_manager:
                return
                
            # Berechne den relativen Pfad vom Projektverzeichnis aus
            rel_path = os.path.relpath(file_path, self.sonos_manager.project_dir)
            url_path = rel_path.replace("\\", "/")
            sound_url = f"http://{self.sonos_manager.http_server_ip}:{self.sonos_manager.http_server_port}/{url_path}"
            
            # Registriere im Sound-Map des Sonos-Managers
            self.sonos_manager.sound_map[sound_id] = {
                "path": file_path,
                "category": "tts",
                "filename": os.path.basename(file_path),
                "format": ".mp3",
                "url": sound_url
            }
            
            self.logger.debug(f"Audio in Sonos-Map registriert: {sound_id} -> {sound_url}")
        except Exception as e:
            self.logger.error(f"Fehler bei der Registrierung im Sonos-Manager: {e}")
    
    def _generate_speech(self, text: str) -> Optional[Tuple[AudioSegment, str]]:
        """
        Generiert Sprachausgabe für den gegebenen Text.
        
        Returns:
            Optional[Tuple[AudioSegment, str]]: Tuple aus Audio-Daten und Cache-Pfad oder None bei Fehler
        """
        try:
            # Bereinige alte Cache-Dateien
            self._clean_old_cache_files()
            
            # Generiere einen konsistenten Hash basierend auf dem Text
            text_hash = self._get_text_hash(text)
            filename = f"tts_{text_hash}"
            sound_id = filename  # Sound-ID ohne Erweiterung
            cache_path = os.path.join(self.cache_dir, f"{filename}.mp3")
            
            # Prüfe, ob die Datei bereits im Cache ist
            if os.path.exists(cache_path):
                self.logger.info(f"🔄 Verwende gecachte TTS-Datei: {filename}")
                # Stelle sicher, dass die Datei im Sonos-Manager registriert ist
                if self.use_sonos and self.sonos_manager:
                    self._register_with_sonos_manager(sound_id, cache_path)
                    
                audio = AudioSegment.from_file(cache_path, format="mp3")
                return audio, cache_path
            
            # Generiere die Sprachdatei mit OpenAI
            self.logger.info(f"🔊 Generiere neue TTS-Datei: {filename}")
            response = self.openai.audio.speech.create(
                model="tts-1",
                voice=self.voice,
                input=text
            )
            
            # Speichere die MP3 im Cache
            with open(cache_path, "wb") as f:
                f.write(response.content)
            
            # Registriere im Sonos-Manager
            if self.use_sonos and self.sonos_manager:
                self._register_with_sonos_manager(sound_id, cache_path)
            
            # Lade die MP3 direkt aus der API-Antwort
            audio_stream = BytesIO(response.content)
            audio = AudioSegment.from_file(audio_stream, format="mp3")
            
            return audio, cache_path
            
        except Exception as e:
            self.logger.error("Fehler bei der Sprachgenerierung: %s", e)
            return None
    
    def _play_audio(self, audio_data: AudioSegment, cache_path: str) -> None:
        """
        Spielt die Audio-Daten ab, entweder über Sonos oder lokal.
        
        Args:
            audio_data: Audio-Daten als AudioSegment
            cache_path: Pfad zur Cache-Datei
        """
        with self._audio_lock:
            try:
                if self.use_sonos and self.sonos_manager and self.sonos_manager.sonos_device:
                    # Spielen über Sonos - nutze die Cache-Datei
                    self.logger.debug("Spiele Audio über Sonos ab")
                    
                    # Das tts_sound_id wird aus dem Dateinamen abgeleitet
                    sound_filename = os.path.basename(cache_path)
                    tts_sound_id = os.path.splitext(sound_filename)[0]  # Sound-ID ohne Erweiterung
                    
                    # Stelle sicher, dass der Sound im Sound-Map registriert ist
                    if tts_sound_id not in self.sonos_manager.sound_map:
                        self._register_with_sonos_manager(tts_sound_id, cache_path)
                    
                    # Spiele die Datei auf dem Sonos-Gerät ab
                    self.logger.info(f"🔊 Spiele TTS-Audio '{tts_sound_id}' über Sonos ab")
                    self.sonos_manager.play(tts_sound_id, block=True, volume=0.6)
                else:
                    # Lokale Wiedergabe über pygame
                    self.logger.debug("Spiele Audio lokal über pygame ab")
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
                if not self.use_sonos and pygame.mixer.get_init():
                    pygame.mixer.music.stop()
            
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
                # Stoppe aktuelle Audiowiedergabe
                if self.use_sonos and self.sonos_manager and self.sonos_manager.sonos_device:
                    # Sonos-Wiedergabe stoppen mit Fade-Out
                    self.sonos_manager.stop()
                else:
                    # Lokale Audiowiedergabe stoppen
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
            
            if self.use_sonos and self.sonos_manager and self.sonos_manager.sonos_device:
                # Versuche Sonos direkt zu stoppen
                try:
                    self.sonos_manager.sonos_device.stop()
                except Exception as e:
                    self.logger.error("Fehler beim direkten Stoppen von Sonos: %s", e)
            else:
                try:
                    pygame.mixer.quit()
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                    self.logger.info("Mixer wurde neu gestartet")
                except Exception as e:
                    self.logger.error("Fehler beim Neustart des Mixers: %s", e)
        
        return True

    def _clear_queues(self) -> None:
        """Leert alle Aufgaben-Queues sicher"""
        try:
            with self.text_queue.mutex:
                self.text_queue.queue.clear()
            with self.audio_queue.mutex:
                self.audio_queue.queue.clear()
        except Exception as e:
            self.logger.error("Fehler beim Leeren der Queues: %s", e)
    
    def enqueue_text(self, response_text: str, is_interrupting = True) -> str:
        """
        Fügt Text zur Sprachausgabe hinzu.
        
        Args:
            response_text: Der auszugebende Text
            is_interrupting: Wenn True, wird die aktuelle Wiedergabe unterbrochen
            
        Returns:
            str: Der zur Ausgabe hinzugefügte Text
        """
        self.logger.info("🤖 Assistenten-Antwort: %s", response_text)
        
        if not response_text or response_text.strip() == "":
            self.logger.warning("Leere Antwort erhalten, keine Sprachausgabe")
            return ""
        
        if is_interrupting:
            self.interrupt_and_reset()

        self.text_queue.put(response_text)
        self.logger.info("Text zur Sprachausgabe hinzugefügt: %s", response_text[:50] + ("..." if len(response_text) > 50 else ""))
        
        return response_text