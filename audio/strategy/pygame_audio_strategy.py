import os
import time
import pygame
from io import BytesIO
from pydub import AudioSegment
import pygame

from audio.strategy.audio_manager import SoundInfo
from audio.strategy.audio_playback_strategy import AudioPlaybackStrategy
from util.loggin_mixin import LoggingMixin

class PygameAudioStrategy(AudioPlaybackStrategy, LoggingMixin):
    def __init__(self):
        self._current_volume = 1.0
    
    def initialize(self):
        """Initialisiert den Pygame-Mixer."""
        pygame.mixer.init()
        self.logger.info("✅ Pygame-Audiosystem initialisiert")
    
    def play_sound(self, sound_info: SoundInfo) -> bool:
        """Spielt einen Sound mit Pygame ab."""
        try:
            sound_path = sound_info.path
            
            sound = AudioSegment.from_file(sound_path)
            
            audio_io = BytesIO()
            sound.export(audio_io, format="wav")
            audio_io.seek(0)
            
            pygame_sound = pygame.mixer.Sound(audio_io)
            
            pygame_sound.set_volume(max(0.0, min(1.0, self._current_volume)))
            
            pygame_sound.play()
            
            while pygame.mixer.get_busy():
                pygame.time.wait(100)
                
            return True
                
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Abspielen des Sounds: {e}")
            return False
        finally:
            if 'audio_io' in locals():
                audio_io.close()
    
    def is_playing(self) -> bool:
        return pygame.mixer.get_busy()
    
    def stop_playback(self):
        """Stoppt alle Pygame-Audio-Wiedergaben."""
        pygame.mixer.stop()
    
    def set_volume(self, volume: float):
        """Setzt die Lautstärke für alle aktiven Pygame-Kanäle."""
        self._current_volume = volume
        for i in range(pygame.mixer.get_num_channels()):
            channel = pygame.mixer.Channel(i)
            if channel.get_busy():
                channel.set_volume(volume)
    
    def fade_out(self, duration: float):
        """Führt einen Fade-Out-Effekt für alle Pygame-Kanäle durch."""
        import pygame
        
        if not self.is_playing():
            return
        
        self.logger.info(f"🔉 Führe Fade-Out über {duration} Sekunden durch...")
        
        start_volume = self._current_volume
        
        steps = int(duration * 20)
        
        volume_step = start_volume / steps if steps > 0 else 0
        
        time_step = duration / steps if steps > 0 else 0
        
        for step in range(steps):
            current_volume = start_volume - (volume_step * step)
            current_volume = max(0.0, current_volume)
            
            for i in range(pygame.mixer.get_num_channels()):
                channel = pygame.mixer.Channel(i)
                if channel.get_busy():
                    channel.set_volume(current_volume)
            
            time.sleep(time_step)
        
        pygame.mixer.stop()
        self.logger.info("🔇 Fade-Out abgeschlossen")