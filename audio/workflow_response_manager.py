import os
import hashlib
from typing import Dict
from openai import OpenAI
from audio.audio_manager import play, get_mapper

class WorkflowResponseManager:
    """Manages TTS responses with caching for standard messages."""
    
    def __init__(self, voice="nova", category="light_responses", output_dir="audio/sounds/standard_phrases"):
        self.openai = OpenAI()
        self.voice = voice
        self.category = category
        self.output_dir = output_dir
        self.cache_dir = os.path.join(output_dir, category)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Get audio manager to work with it directly
        self.audio_manager = get_mapper()
        
        # In-memory cache for mapping between message texts and filenames
        self._message_cache: Dict[str, str] = {}
        
        # Initialize cache from existing files
        self._load_cache()
    
    def _load_cache(self):
        """Load existing audio files into the message cache."""
        if not os.path.exists(self.cache_dir):
            return
            
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".mp3"):
                # Extract the message hash from the filename
                # Format is tts_category_HASH.mp3
                parts = filename.split('_')
                if len(parts) >= 3:
                    # Get hash part (before the extension)
                    hash_part = parts[2].split('.')[0]
                    
                    # Store in cache (we don't know the original message text, 
                    # but we can use the hash for lookups)
                    self._message_cache[hash_part] = os.path.splitext(filename)[0]
    
    def _get_message_hash(self, message: str) -> str:
        return hashlib.md5(message.encode('utf-8')).hexdigest()[:8]
    
    def _generate_tts_file(self, text: str, message_hash: str) -> str:
        try:
            # Create filename based on hash
            filename = f"tts_{self.category}_{message_hash}"
            file_path = os.path.join(self.cache_dir, f"{filename}.mp3")
            
            # TTS API call
            response = self.openai.audio.speech.create(
                model="tts-1",
                voice=self.voice,
                input=text
            )
            
            # Write content to file
            with open(file_path, "wb") as file:
                file.write(response.content)
            
            print(f"✅ Sprachdatei gespeichert: {file_path}")
            
            # Register the new file in the AudioManager's sound_map
            # This avoids having to re-scan all files
            sound_id = filename  # The stem of the filename (without extension)
            rel_path = os.path.join(self.category, f"{filename}.mp3")
            
            self.audio_manager.sound_map[sound_id] = {
                "path": file_path,
                "category": self.category,
                "filename": f"{filename}.mp3",
                "format": ".mp3"
            }
            
            print(f"🔍 Neue Audiodatei im AudioManager registriert: {sound_id}")
            
            return filename
            
        except Exception as e:
            print(f"❌ Fehler bei der Sprachgenerierung: {e}")
            return None
    
    def play_response(self, message: str) -> str:
        """
        Play a TTS response for the given message.
        If the message already has a TTS file, it will be played.
        Otherwise, a new TTS file will be generated.
        
        Args:
            message: The text message to play
            
        Returns:
            The original message text
        """
        if not message.strip():
            return message
            
        message_hash = self._get_message_hash(message)
        
        # Check if we already have this message in cache
        if message_hash in self._message_cache:
            # Play the cached file
            cached_filename = self._message_cache[message_hash]
            print(f"🔊 Spiele gecachte Audio: {cached_filename}")
            play(cached_filename)
        else:
            # Check if file exists on disk but not in memory cache
            filename = f"tts_{self.category}_{message_hash}"
            file_path = os.path.join(self.cache_dir, f"{filename}.mp3")
            
            if os.path.exists(file_path):
                # File exists, add to cache and play
                self._message_cache[message_hash] = filename
                
                # Make sure it's registered in the AudioManager
                if filename not in self.audio_manager.sound_map:
                    self.audio_manager.sound_map[filename] = {
                        "path": file_path,
                        "category": self.category,
                        "filename": f"{filename}.mp3",
                        "format": ".mp3"
                    }
                
                play(filename)
            else:
                # Generate new file
                new_filename = self._generate_tts_file(message, message_hash)
                if new_filename:
                    # Add to cache
                    self._message_cache[message_hash] = new_filename
                    # Play the file
                    play(new_filename)
        
        return message
    
    def refresh_sound_map(self):
        """Force AudioManager to rescan all audio files."""
        self.audio_manager._discover_sounds()
        print("🔄 AudioManager-Sound-Map aktualisiert")