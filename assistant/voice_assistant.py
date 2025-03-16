import os
import shutil
from openai import OpenAI
from io import BytesIO
from pydub import AudioSegment
import pygame
import threading
import queue
import uuid

class VoiceGenerator:
    def __init__(self, voice="nova", cache_dir="/tmp/tts_cache"):
        """Initialisiert den TTS Generator mit OpenAI API und Vorausverarbeitung"""
        self.openai = OpenAI()
        self.voice = voice
        self.cache_dir = cache_dir
        
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self._setup_ffmpeg()
        self._setup_pygame()
        self._audio_lock = threading.Lock()
        
        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()  
        
        self.active = True
        self.tts_worker = threading.Thread(target=self._process_tts_queue, daemon=True)
        self.tts_worker.start()
        
        self.playback_worker = threading.Thread(target=self._process_audio_queue, daemon=True)
        self.playback_worker.start()
        
    def _setup_ffmpeg(self):
        """Überprüft und setzt den FFmpeg-Pfad, falls nötig"""
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            print(f"✅ FFmpeg gefunden: {ffmpeg_path}")
        else:
            print("❌ FFmpeg nicht gefunden! Bitte installieren oder Pfad setzen.")
            os.environ["PATH"] += os.pathsep + r"C:\ffmpeg-2025-02-17-git-b92577405b-essentials_build\bin"
            
    def _setup_pygame(self):
        """Initialisiert den pygame Mixer für die Audiowiedergabe"""
        try:
            pygame.mixer.quit()  
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        except Exception as e:
            print(f"❌ Pygame Initialisierungsfehler: {e}")
    
    def _process_tts_queue(self):
        """Worker-Thread, der Texte in Audio umwandelt und zur Wiedergabe vorbereitet"""
        while self.active:
            try:
                text = self.text_queue.get(timeout=0.5)
                
                if not text.strip():
                    self.text_queue.task_done()
                    continue
                
                audio_data = self._generate_speech(text)
                
                if audio_data:
                    self.audio_queue.put((text, audio_data))
                
                self.text_queue.task_done()
                
            except queue.Empty:
                pass
            except Exception as e:
                print(f"❌ TTS-Verarbeitungsfehler: {e}")
    
    def _process_audio_queue(self):
        """Worker-Thread, der vorbereitete Audiodateien abspielt"""
        while self.active:
            try:
                # Hole die nächste Audio-Datei aus der Queue
                text, audio_data = self.audio_queue.get(timeout=0.5)
                
                # Spiele die Audio-Datei ab
                self._play_audio(audio_data)
                
                # Markiere Aufgabe als erledigt
                self.audio_queue.task_done()
                
            except queue.Empty:
                # Queue Timeout, setze Schleife fort
                pass
            except Exception as e:
                print(f"❌ Audio-Wiedergabefehler: {e}")
    
    def _generate_speech(self, text):
        """Generiert Sprache mit OpenAI TTS und gibt das Audio-Segment zurück"""
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
            print(f"❌ Fehler bei der Sprachgenerierung: {e}")
            return None
    
    def _play_audio(self, audio_data):
        """Spielt die Audiodaten ab mit Sperrmechanismus zur Vermeidung überlappender Wiedergabe"""
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
                print(f"❌ Wiedergabefehler: {e}")
            finally:
                pygame.mixer.music.stop()
                audio_io.close()

    def speak(self, text):
        """Fügt einen Text zur Sprachqueue für die Verarbeitung hinzu.
        interrupt=True bewirkt, dass vorherige Aufträge abgebrochen werden."""
        if not text.strip():
            return

        self.interrupt_and_reset()
        self.text_queue.put(text)
            
    def interrupt_and_reset(self):
        """Unterbricht die aktuelle Sprachausgabe und leert die Queues mit Deadlock-Vermeidung."""
        
        print("Unterbreche aktuelle Audioausgabe...")
        
        # Versuche, das Lock zu erwerben, aber mit Timeout
        lock_acquired = self._audio_lock.acquire(timeout=1.0)  # 1 Sekunde Timeout
        
        try:
            if lock_acquired:
                # Lock erfolgreich erworben, führe normale Operationen aus
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    try:
                        pygame.mixer.music.unload()
                    except:
                        pass
                        
                # Queue-Clearing mit Timeout-Schutz
                try:
                    with self.text_queue.mutex:
                        self.text_queue.queue.clear()
                except:
                    print("Warnung: Konnte Text-Queue nicht leeren")
                    
                try:
                    with self.audio_queue.mutex:
                        self.audio_queue.queue.clear()
                except:
                    print("Warnung: Konnte Audio-Queue nicht leeren")
                    
                print("🎤 Wake Word erkannt - System bereit für neue Eingabe")
            else:
                # Lock konnte nicht erworben werden, notfallmäßiges Anhalten
                print("⚠️ Konnte Audio-Lock nicht erwerben, versuche alternative Stopstrategie")
                
                # Brutaler Ansatz: Mixer neu starten ohne Lock
                try:
                    pygame.mixer.quit()
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                    print("🔄 Mixer wurde neu gestartet")
                except Exception as e:
                    print(f"❌ Fehler beim Neustart des Mixers: {e}")
        finally:
            # Stelle sicher, dass das Lock freigegeben wird
            if lock_acquired:
                self._audio_lock.release()
        
        return True

    def _clear_queues(self):
        with self.text_queue.mutex:
            self.text_queue.queue.clear()
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()