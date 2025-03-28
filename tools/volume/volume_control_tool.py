import asyncio
from langchain.tools import tool
from audio.strategy.audio_manager import get_audio_manager
from audio.workflow_audio_response_manager import WorkflowAudioResponseManager

# Kurze, prägnante Antworttexte
VOLUME_SET_SUCCESS = "Lautstärke auf {level} von 10 gesetzt."
VOLUME_INCREASE_SUCCESS = "Lautstärke auf {percent} Prozent erhöht."
VOLUME_DECREASE_SUCCESS = "Lautstärke auf {percent} Prozent verringert."
VOLUME_GET_CURRENT = "Lautstärke beträgt {percent} Prozent."
VOLUME_ERROR_RANGE = "Lautstärke muss zwischen 1 und 10 liegen."
VOLUME_ERROR_MISSING = "Bitte gib einen Lautstärkewert an."

audio_system = get_audio_manager()

# TODO: Er benutzt diesen Streamer hier scheinbar auch nicht leider :()

workflow_audio_response_manager = WorkflowAudioResponseManager(
    category="volume_responses",
)

def run_async(coro):
    return asyncio.run(coro)

@tool("set_volume", return_direct=True)
def set_volume(level: int):
    """Setzt die Systemlautstärke auf einen bestimmten Level.
    
    Args:
        level: Lautstärkelevel zwischen 1 und 10
    """
    try:
        if not 1 <= level <= 10:
            return workflow_audio_response_manager.respond_with_audio(VOLUME_ERROR_RANGE)
        
        # Umrechnung von 1-10 Skala zu 0-100% Skala und direkt über Property setzen
        percent = level * 10
        audio_system.volume = percent / 100.0
        
        # Hier wird jetzt der Level anstelle des Prozentsatzes ausgegeben
        response = VOLUME_SET_SUCCESS.format(level=level)
        return workflow_audio_response_manager.respond_with_audio(response)
    except Exception as e:
        error_msg = f"Fehler bei Lautstärke: {str(e)}"
        return workflow_audio_response_manager.respond_with_audio(error_msg)

@tool("increase_volume", return_direct=True)
def increase_volume(step: int = 15):
    """Erhöht die Systemlautstärke um einen bestimmten Prozentsatz.
    
    Args:
        step: Erhöhungsschrittweite in Prozent (Standard: 15%)
    """
    try:
        current = int(audio_system.volume * 100)
        new_volume = min(100, current + step)
        
        audio_system.volume = new_volume / 100.0
        
        response = VOLUME_INCREASE_SUCCESS.format(percent=new_volume)
        return workflow_audio_response_manager.respond_with_audio(response)
    except Exception as e:
        error_msg = f"Fehler bei Lautstärke: {str(e)}"
        return workflow_audio_response_manager.respond_with_audio(error_msg)

@tool("decrease_volume", return_direct=True)
def decrease_volume(step: int = 15):
    """Verringert die Systemlautstärke um einen bestimmten Prozentsatz.
    
    Args:
        step: Verringerungsschrittweite in Prozent (Standard: 15%)
    """
    try:
        # Aktuelle Lautstärke abrufen und prozentual verringern
        current = int(audio_system.volume * 100)
        new_volume = max(0, current - step)
        
        # Neue Lautstärke setzen
        audio_system.volume = new_volume / 100.0
        
        response = VOLUME_DECREASE_SUCCESS.format(percent=new_volume)
        return workflow_audio_response_manager.respond_with_audio(response)
    except Exception as e:
        error_msg = f"Fehler bei Lautstärke: {str(e)}"
        return workflow_audio_response_manager.respond_with_audio(error_msg)

@tool("get_volume", return_direct=True)
def get_volume():
    """Gibt die aktuelle Systemlautstärke zurück."""
    try:
        # Lautstärke direkt aus AudioManager als Prozent holen
        current_volume = int(audio_system.volume * 100)
        
        response = VOLUME_GET_CURRENT.format(percent=current_volume)
        return workflow_audio_response_manager.respond_with_audio(response)
    except Exception as e:
        error_msg = f"Fehler bei Lautstärke: {str(e)}"
        return workflow_audio_response_manager.respond_with_audio(error_msg)

def get_volume_tools():
    """Gibt eine Liste aller verfügbaren Volume-Tools zurück."""
    return [
        set_volume,
        increase_volume,
        decrease_volume,
        get_volume
    ]