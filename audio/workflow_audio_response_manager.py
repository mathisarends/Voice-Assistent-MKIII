import os
import hashlib
from typing import Dict, Optional
from openai import OpenAI
from audio.strategy.audio_manager import AudioManager
from util.decorator import log_exceptions_from_self_logger
from util.loggin_mixin import LoggingMixin

class WorkflowAudioResponseManager(LoggingMixin):
    def __init__(self, voice="nova", category="light_responses", output_dir="audio/sounds/standard_phrases"):
        self.openai = OpenAI()
        self.voice = voice
        self.category = category
        self.output_dir = output_dir
        self.cache_dir = os.path.join(output_dir, category)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.audio_manager = AudioManager()
        self._message_cache: Dict[str, str] = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        if not os.path.exists(self.cache_dir):
            return
            
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith(".mp3"):
                continue
                
            parts = filename.split('_')
            if len(parts) < 3:
                continue
                
            hash_part = parts[2].split('.')[0]
            self._message_cache[hash_part] = os.path.splitext(filename)[0]
    
    def _get_message_hash(self, message: str) -> str:
        return hashlib.md5(message.encode('utf-8')).hexdigest()[:8]
    
    @log_exceptions_from_self_logger("beim Registrieren der Audiodatei")
    def _register_sound(self, sound_id: str, file_path: str) -> bool:
        """Registriert eine Audiodatei im AudioManager.
        """
        abs_file_path = os.path.abspath(file_path)
        if not os.path.exists(abs_file_path):
            self.logger.error(f"❌ Datei existiert nicht: {abs_file_path}")
            return False

        project_dir = self.audio_manager.project_dir
        rel_path = os.path.relpath(abs_file_path, project_dir)

        if not self.audio_manager.register_sound(sound_id, abs_file_path, self.category):
            self.logger.error(f"❌ Registrierung fehlgeschlagen: {sound_id}")
            return False
            
        self.logger.info(f"🔍 Neue Audiodatei registriert: {sound_id} -> {rel_path}")
        return True
        
    @log_exceptions_from_self_logger("bei der Sprachgenerierung (TTS)")
    def _generate_tts_file(self, text: str, message_hash: str) -> Optional[str]:
        """Generiert eine TTS-Audiodatei für den gegebenen Text."""
        filename = f"tts_{self.category}_{message_hash}"
        file_path = os.path.join(self.cache_dir, f"{filename}.mp3")
        
        response = self.openai.audio.speech.create(
            model="tts-1",
            voice=self.voice,
            input=text
        )
        
        with open(file_path, "wb") as file:
            file.write(response.content)
        
        self.logger.info(f"✅ Sprachdatei gespeichert: {file_path}")
        
        if not self._register_sound(filename, file_path):
            return None
            
        return filename
    
    def _get_sound_from_cache(self, message_hash: str) -> Optional[str]:
        """Sucht nach einem gecachten Sound für den Hash.
        """
        if message_hash not in self._message_cache:
            return None
            
        sound_id = self._message_cache[message_hash]
        self.logger.info(f"🔊 Spiele gecachte Audio: {sound_id}")
        return sound_id
    
    def _get_sound_from_file(self, message_hash: str) -> Optional[str]:
        """Prüft, ob eine Audiodatei für den Hash existiert.
        """
        filename = f"tts_{self.category}_{message_hash}"
        file_path = os.path.join(self.cache_dir, f"{filename}.mp3")
        
        if not os.path.exists(file_path):
            return None
            
        self._message_cache[message_hash] = filename
        self._register_sound(filename, file_path)
        return filename
    
    def play_response(self, message: str) -> str:
        """Spielt eine Audioantwort für die Nachricht ab.
        """
        if not message.strip():
            return message
            
        message_hash = self._get_message_hash(message)
        
        sound_id = self._get_sound_from_cache(message_hash)
        if sound_id:
            self.audio_manager.play(sound_id)
            return message
        
        sound_id = self._get_sound_from_file(message_hash)
        if sound_id:
            self.audio_manager.play(sound_id)
            return message
        
        sound_id = self._generate_tts_file(message, message_hash)
        if sound_id:
            self._message_cache[message_hash] = sound_id
            self.audio_manager.play(sound_id)
        
        return message
    
    def respond_with_audio(self, message: str) -> str:
        """Alias für play_response."""
        return self.play_response(message)