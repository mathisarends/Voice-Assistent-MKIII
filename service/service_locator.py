from integrations.phillips_hue.bridge import HueBridge
from integrations.phillips_hue.light_controller import LightController
from integrations.spotify.spotify_api import SpotifyPlaybackController
from service.human_speech import AudioTranscriber, SpeechRecorder
from service.speech_service import SpeechService
from service.wake_word_listener import WakeWordListener

# Hier will ich eigentlich eine config, die es mir auch erlaubt die Lichter, Spotify-Clients etc. zuzugreifen
# SpotifySound muss weggedrückt werden wenn ein Wakeword erkannt wird oder der Assistent spricht.

class ServiceLocator:
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'ServiceLocator':
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.initialize_all_services()
        return cls._instance
    
    def __init__(self):
        self.speech_service = None
        self.audio_transcriber = None
    
    def initialize_all_services(self):
        """Initialisiert alle Services beim ersten Aufruf von get_instance"""
        self.speech_recorder = SpeechRecorder()
        self.audio_transcriber = AudioTranscriber()
        self.speech_service = SpeechService()
        
        bridge = HueBridge.connect_by_ip()
        self.lighting_controller = LightController(bridge)
        
        self.spotify_player = SpotifyPlaybackController()
        
        self.wake_word_listener = WakeWordListener()
        
    
    def get_speech_service(self) -> 'SpeechService':
        return self.speech_service
    
    def get_audio_transcriber(self) -> 'AudioTranscriber':
        return self.audio_transcriber
    
    def get_speech_recorder(self) -> 'SpeechRecorder':
        return self.speech_recorder
    
    def get_lighting_controller(self) -> 'LightController':
        return self.lighting_controller#
    
    def get_wake_word_listener(self) -> 'WakeWordListener':
        return self.wake_word_listener
    

service_locator = ServiceLocator.get_instance()