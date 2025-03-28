import os
import hashlib
import time
from typing import Optional, Dict, Tuple

from openai import OpenAI
from audio.strategy.audio_manager import get_audio_manager
from util.loggin_mixin import LoggingMixin
from util.decorator import log_exceptions_from_self_logger
from singleton_decorator import singleton

@singleton
class TTSGenerator(LoggingMixin):
    """
    Zentrale Klasse für die Generierung und Verwaltung von TTS-Audiodateien.
    Stellt sicher, dass TTS-Dateien nur einmal generiert und wiederverwendet werden.
    """
    
    def __init__(self, default_base_cache_dir="audio/sounds"):
        """
        Initialisiert den TTS-Generator.
        """
        super().__init__()
        self.openai = OpenAI()
        self.project_dir = os.path.abspath(os.path.curdir)
        self.default_base_cache_dir = os.path.join(self.project_dir, default_base_cache_dir)
        
        self.audio_manager = get_audio_manager()
        
        self._message_cache: Dict[str, Dict[str, str]] = {}
        
        self._category_paths: Dict[str, str] = {}
        
        self._last_cleanup_time = time.time()
        self.cache_cleanup_interval = 3600
        
        self.logger.info(f"TTS-Generator initialisiert mit Standard-Cache-Verzeichnis: {self.default_base_cache_dir}")
    
    def set_category_path(self, category: str, custom_path: str) -> None:
        """
        Setzt einen benutzerdefinierten Pfad für eine Kategorie.
        """
        if not os.path.isabs(custom_path):
            abs_path = os.path.join(self.project_dir, custom_path)
        else:
            abs_path = custom_path
            
        self._category_paths[category] = abs_path
        os.makedirs(abs_path, exist_ok=True)
        self.logger.info(f"Kategorie '{category}' verwendet nun Pfad: {abs_path}")
        
        if category in self._message_cache:
            del self._message_cache[category]
            self.load_existing_cache(category)
    
    def _get_text_hash(self, text: str) -> str:
        """
        Erzeugt einen konsistenten Hash für einen Text.
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]
    
    def _get_cache_dir(self, category: str) -> str:
        """
        Erstellt und gibt das Cache-Verzeichnis für eine Kategorie zurück.
        Verwendet benutzerdefinierte Pfade, wenn vorhanden.
        """
        if category in self._category_paths:
            cache_dir = self._category_paths[category]
        else:
            cache_dir = os.path.join(self.default_base_cache_dir, category)
            
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    
    @log_exceptions_from_self_logger("bei der TTS-Generierung")
    def generate_tts(self, text: str, category: str = "tts_responses", voice: str = "nova") -> Optional[str]:
        """
        Generiert eine TTS-Audiodatei für einen Text oder verwendet eine vorhandene.
        """
        if not text.strip():
            return None
            
        text_hash = self._get_text_hash(text)
        
        if category not in self._message_cache:
            self._message_cache[category] = {}
            
        if text_hash in self._message_cache[category]:
            sound_id = self._message_cache[category][text_hash]
            self.logger.debug(f"Verwende gecachte TTS-Referenz: {sound_id}")
            return sound_id
        
        filename = f"tts_{category}_{text_hash}"
        cache_dir = self._get_cache_dir(category)
        file_path = os.path.join(cache_dir, f"{filename}.mp3")
        
        if os.path.exists(file_path):
            self.logger.info(f"🔄 Verwende existierende TTS-Datei: {filename}")
            
            self._message_cache[category][text_hash] = filename
            
            if filename not in self.audio_manager.sound_map:
                abs_file_path = os.path.abspath(file_path)
                self.audio_manager.register_sound(filename, abs_file_path, category)
                
            return filename
        
        self.logger.info(f"🔊 Generiere neue TTS-Datei für Text: {text[:50]}...")
        
        try:
            response = self.openai.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            with open(file_path, "wb") as f:
                f.write(response.content)
                
            self.logger.info(f"✅ TTS-Datei gespeichert: {file_path}")
            
            self._message_cache[category][text_hash] = filename
            
            abs_file_path = os.path.abspath(file_path)
            if not self.audio_manager.register_sound(filename, abs_file_path, category):
                self.logger.error(f"❌ Konnte Sound nicht im AudioManager registrieren: {filename}")
                return None
                
            return filename
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei TTS-Generierung: {e}")
            return None
    
    @log_exceptions_from_self_logger("bei der Cache-Bereinigung")
    def clean_old_cache_files(self, max_age_seconds: int = None):
        """
        Löscht alte Cache-Dateien.
        
        Args:
            max_age_seconds: Maximales Alter der Dateien in Sekunden (Standard: cache_cleanup_interval)
        """
        current_time = time.time()
        
        if (current_time - self._last_cleanup_time < self.cache_cleanup_interval) and max_age_seconds is None:
            return
            
        self.logger.info("🧹 Räume alte TTS-Cache-Dateien auf...")
        
        if max_age_seconds is None:
            max_age_seconds = self.cache_cleanup_interval
            
        cleanup_time = current_time - max_age_seconds
        
        self._clean_directory(self.default_base_cache_dir, cleanup_time)
        
        for category, path in self._category_paths.items():
            if os.path.exists(path) and os.path.isdir(path):
                self._clean_directory(path, cleanup_time, is_category_dir=True, category_name=category)
        
        self._last_cleanup_time = current_time
        self.logger.info("🧹 Cache-Bereinigung abgeschlossen")
    
    def _clean_directory(self, directory: str, cleanup_time: float, is_category_dir: bool = False, category_name: str = None):
        """
        Bereinigt ein Verzeichnis von alten Dateien.
        """
        if not os.path.exists(directory):
            return
            
        if is_category_dir:
            self._clean_category_dir(directory, cleanup_time, category_name)
        else:
            for category_dir in os.listdir(directory):
                category_path = os.path.join(directory, category_dir)
                if os.path.isdir(category_path):
                    self._clean_category_dir(category_path, cleanup_time, category_dir)
    
    def _clean_category_dir(self, category_path: str, cleanup_time: float, category: str):
        """
        Bereinigt ein Kategorie-Verzeichnis.
        """
        for filename in os.listdir(category_path):
            if not filename.endswith('.mp3'):
                continue
                
            file_path = os.path.join(category_path, filename)
            try:
                file_mod_time = os.path.getmtime(file_path)
                
                if file_mod_time < cleanup_time:
                    sound_id = os.path.splitext(filename)[0]
                    
                    if sound_id in self.audio_manager.sound_map:
                        with self.audio_manager._lock:
                            del self.audio_manager.sound_map[sound_id]
                    
                    os.remove(file_path)
                    self.logger.debug(f"Gelöschte Cache-Datei: {file_path}")
                    
                    if category in self._message_cache:
                        for hash_key, cached_id in list(self._message_cache[category].items()):
                            if cached_id == sound_id:
                                del self._message_cache[category][hash_key]
                                break
            except Exception as e:
                self.logger.error(f"Fehler beim Verarbeiten von {file_path}: {e}")
    
    @log_exceptions_from_self_logger("beim Laden des Caches")
    def load_existing_cache(self, category: str):
        """
        Lädt existierende TTS-Dateien einer Kategorie in den Memory-Cache.
s        """
        cache_dir = self._get_cache_dir(category)
        
        if not os.path.exists(cache_dir):
            self.logger.warning(f"Cache-Verzeichnis für Kategorie '{category}' existiert nicht: {cache_dir}")
            return
            
        if category not in self._message_cache:
            self._message_cache[category] = {}
            
        loaded_count = 0
        
        for filename in os.listdir(cache_dir):
            if not filename.endswith(".mp3"):
                continue
                
            parts = filename.split('_')
            if len(parts) < 3:
                continue
                
            hash_part = parts[2].split('.')[0]
            sound_id = os.path.splitext(filename)[0]
            
            self._message_cache[category][hash_part] = sound_id
            
            file_path = os.path.join(cache_dir, filename)
            abs_path = os.path.abspath(file_path)
            
            if sound_id not in self.audio_manager.sound_map:
                self.audio_manager.register_sound(sound_id, abs_path, category)
                
            loaded_count += 1
                
        self.logger.info(f"Geladen: {loaded_count} TTS-Einträge für Kategorie '{category}' aus {cache_dir}")

def get_tts_generator() -> TTSGenerator:
    """Gibt die globale TTSGenerator-Instanz zurück."""
    return TTSGenerator()