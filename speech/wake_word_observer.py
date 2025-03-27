from abc import ABC, abstractmethod
from typing import List
from typing_extensions import override

from audio.strategy.audio_manager import AudioManager
from tools.spotify.spotify_controller import SpotifyController
from tools.spotify.spotify_device_manager import SpotifyDeviceManager
from tools.spotify.spotify_player import SpotifyPlayer

# TODO: State Pattern implementieren -> Damit kann man dann auch wesenltich die Loop Logik verkürzen würde ich sagen:

class WakeWordObserver(ABC):
    @abstractmethod
    def on_wakeword_detected(self):
        """Wird aufgerufen, wenn das Wake-Word erkannt wurde."""
        pass

class WakeWordAudioFeedbackObserver(WakeWordObserver):
    @override
    def on_wakeword_detected(self):
        AudioManager().play("wakesound")
        
class SpotifyVolumeAdjustmentObserver(WakeWordObserver):
    def __init__(self):
        player = SpotifyPlayer()
        device_manager = SpotifyDeviceManager()
    
        self.controller = SpotifyController(player, device_manager)
    
    @override    
    def on_wakeword_detected(self):
        self.controller.set_volume(37.5)
       
# Hier muss ich nohcmal mit einer Animation ran 
class LightControlObserver(WakeWordObserver):
    @override
    def on_wakeword_detected(self):
        print("🔦 Licht wird eingeschaltet")
        
def get_wake_word_observers() -> List[WakeWordObserver]:
    return [
        WakeWordAudioFeedbackObserver(),
        SpotifyVolumeAdjustmentObserver()
    ]