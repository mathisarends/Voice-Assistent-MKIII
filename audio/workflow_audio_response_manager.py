import os
import hashlib
from typing import Dict
from openai import OpenAI
from audio.audio_manager import play, get_mapper
from util.loggin_mixin import LoggingMixin

class WorkflowAudioResponseManager(LoggingMixin):
    def __init__(self, voice="nova", category="light_responses", output_dir="audio/sounds/standard_phrases"):
        self.openai = OpenAI()
        self.voice = voice
        self.category = category
        self.output_dir = output_dir
        self.cache_dir = os.path.join(output_dir, category)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.audio_manager = get_mapper()
        self._message_cache: Dict[str, str] = {}
        self._load_cache()
    
    def _load_cache(self):
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
    
    def _generate_tts_file(self, text: str, message_hash: str) -> str:
        try:
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
            
            # Register in AudioManager
            self.audio_manager.sound_map[filename] = {
                "path": file_path,
                "category": self.category,
                "filename": f"{filename}.mp3",
                "format": ".mp3"
            }
            
            self.logger.info(f"🔍 Neue Audiodatei registriert: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei der Sprachgenerierung: {e}")
            return None
    
    def play_response(self, message: str) -> str:
        if not message.strip():
            return message
            
        message_hash = self._get_message_hash(message)
        
        # Return early if in cache
        if message_hash in self._message_cache:
            cached_filename = self._message_cache[message_hash]
            self.logger.info(f"🔊 Spiele gecachte Audio: {cached_filename}")
            play(cached_filename)
            return message
        
        # Check existing file
        filename = f"tts_{self.category}_{message_hash}"
        file_path = os.path.join(self.cache_dir, f"{filename}.mp3")
        
        if os.path.exists(file_path):
            self._message_cache[message_hash] = filename
            
            # Ensure registered in AudioManager
            if filename not in self.audio_manager.sound_map:
                self.audio_manager.sound_map[filename] = {
                    "path": file_path,
                    "category": self.category,
                    "filename": f"{filename}.mp3",
                    "format": ".mp3"
                }
            
            play(filename)
            return message
        
        # Generate new file
        new_filename = self._generate_tts_file(message, message_hash)
        if new_filename:
            self._message_cache[message_hash] = new_filename
            play(new_filename)
        
        return message
    
    def respond_with_audio(self, message):
        return self.play_response(message)