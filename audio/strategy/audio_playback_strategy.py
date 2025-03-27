import os
import time
from pathlib import Path
from abc import ABC, abstractmethod
import pygame


class AudioPlaybackStrategy(ABC):
    """Abstract base class for audio playback strategies."""
    
    @abstractmethod
    def initialize(self):
        """Initialize the audio system."""
        pass
    
    @abstractmethod
    def play_sound(self, sound_path: str, volume: float) -> bool:
        """Play a sound file."""
        pass
    
    @abstractmethod
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        pass
    
    @abstractmethod
    def stop_playback(self):
        """Stop the current playback."""
        pass
    
    @abstractmethod
    def set_volume(self, volume: float):
        """Set the volume level."""
        pass
    
    @abstractmethod
    def fade_out(self, duration: float):
        """Perform a fade out effect."""
        pass