from typing import Dict, Type, Optional
from audio.strategy.audio_playback_strategy import AudioPlaybackStrategy
from singleton_decorator import singleton

@singleton
class AudioStrategyFactory:
    """
    Factory-Klasse für die Erstellung von Audio-Wiedergabe-Strategien.
    
    Diese Klasse verwaltet die Erstellung verschiedener Audio-Strategien und
    ermöglicht eine einfache Erweiterung um neue Strategien ohne Änderung der API.
    """
    
    def __init__(self):
        self._strategies: Dict[str, Type[AudioPlaybackStrategy]] = {}
        self._registered = False
    
    def register_strategies(self):
        if self._registered:
            return
            
        from audio.strategy.pygame_audio_strategy import PygameAudioStrategy
        from audio.strategy.sonos_playback_strategy import SonosAudioStrategy
        
        self._strategies = {
            'pygame': PygameAudioStrategy,
            'sonos': SonosAudioStrategy,
        }
        
        self._registered = True
    
    def create_strategy(self, strategy_type: str, **kwargs) -> AudioPlaybackStrategy:
        """
        Erstellt eine Audio-Strategie basierend auf dem angegebenen Typ.
        
        Args:
            strategy_type: Name der zu erstellenden Strategie ('pygame', 'sonos', etc.)
            **kwargs: Zusätzliche Parameter für den Konstruktor der Strategie
            
        Returns:
            Eine initialisierte Instanz der angeforderten AudioPlaybackStrategy
            
        Raises:
            ValueError: Wenn der angegebene Strategie-Typ nicht existiert
        """
        self.register_strategies()
        
        if strategy_type not in self._strategies:
            valid_types = ', '.join(self._strategies.keys())
            raise ValueError(f"Unbekannter Strategie-Typ: '{strategy_type}'. Verfügbare Typen: {valid_types}")
        
        strategy_class = self._strategies[strategy_type]
        return strategy_class(**kwargs)
    
    def create_pygame_strategy(self) -> AudioPlaybackStrategy:
        return self.create_strategy('pygame')
    
    def create_sonos_strategy(self, 
                             speaker_name: Optional[str] = None, 
                             speaker_ip: Optional[str] = None, 
                             http_server_port: int = 8000) -> AudioPlaybackStrategy:
        return self.create_strategy('sonos', 
                                   speaker_name=speaker_name,
                                   speaker_ip=speaker_ip, 
                                   http_server_port=http_server_port)
    
    def get_available_strategies(self) -> list:
        self.register_strategies()
        return list(self._strategies.keys())