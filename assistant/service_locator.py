from assistant.speech_service import SpeechService
from speech.recognition.audio_transcriber import AudioTranscriber
from speech.recognition.whisper_speech_recognition import \
    WhisperSpeechRecognition


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
        self.speech_recorder = WhisperSpeechRecognition()
        self.audio_transcriber = AudioTranscriber()
        self.speech_service = SpeechService()
    
    def get_speech_service(self) -> 'SpeechService':
        return self.speech_service
    
    def get_audio_transcriber(self) -> 'AudioTranscriber':
        return self.audio_transcriber
    
    def get_speech_recorder(self) -> 'WhisperSpeechRecognition':
        return self.speech_recorder
    

service_locator = ServiceLocator.get_instance()