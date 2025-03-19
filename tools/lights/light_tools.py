import asyncio
from langchain.tools import tool

from audio.workflow_audio_response_manager import WorkflowAudioResponseManager
from tools.lights.bridge.bridge import HueBridge
from tools.lights.hue_controller import HueController

SCENE_NEXT_SUCCESS = "Zur nächsten Lichtszene gewechselt."
SCENE_PREVIOUS_SUCCESS = "Zur vorherigen Lichtszene gewechselt."
SCENE_ACTIVATE_SUCCESS = "Lichtszene '{scene_name}' wurde aktiviert."
SCENE_LIST_EMPTY = "Keine Lichtszenen gefunden."
SCENE_LIST_SUCCESS = "Verfügbare Lichtszenen: {scenes}"
LIGHT_ON_SUCCESS = "Alle Lichter wurden eingeschaltet."
LIGHT_OFF_SUCCESS = "Alle Lichter wurden ausgeschaltet."
BRIGHTNESS_ADJUST_INCREASE = "Helligkeit wurde um {value}% erhöht."
BRIGHTNESS_ADJUST_DECREASE = "Helligkeit wurde um {value}% verringert."
BRIGHTNESS_SET_SUCCESS = "Helligkeit wurde auf {percent}% gesetzt."

hue_controller = HueController(HueBridge.connect_by_ip())

audio_manager = WorkflowAudioResponseManager(
    category="light_responses",
)

def run_async(coro):
    return asyncio.run(coro)

@tool("list_hue_scenes", return_direct=False)
def list_hue_scenes():
    """Listet alle verfügbaren Philips Hue Lichtszenen auf."""
    try:
        scenes = run_async(hue_controller.get_scene_names())
        return SCENE_LIST_SUCCESS.format(scenes=", ".join(scenes))
    
    except Exception as e:
        error_msg = f"Fehler beim Abrufen der Lichtszenen: {str(e)}"
        return audio_manager.respond_with_audio(error_msg)

@tool("activate_hue_scene", return_direct=True)
def activate_hue_scene(scene_name: str):
    """Aktiviert eine bestimmte Philips Hue Lichtszene anhand ihres Namens.
    
    Args:
        scene_name: Name der zu aktivierenden Lichtszene
    """
    try:
        run_async(hue_controller.activate_scene(scene_name))
        response = SCENE_ACTIVATE_SUCCESS.format(scene_name=scene_name)
        return audio_manager.respond_with_audio(response)
    except Exception as e:
        error_msg = f"Fehler beim Aktivieren der Lichtszene '{scene_name}': {str(e)}"
        return audio_manager.respond_with_audio(error_msg)

@tool("next_hue_scene", return_direct=True)
def next_hue_scene():
    """Wechselt zur nächsten Philips Hue Lichtszene in der aktuellen Gruppe."""
    try:
        run_async(hue_controller.next_scene())
        return audio_manager.respond_with_audio(SCENE_NEXT_SUCCESS)
    except Exception as e:
        error_msg = f"Fehler beim Wechseln zur nächsten Lichtszene: {str(e)}"
        return audio_manager.respond_with_audio(error_msg)
    
@tool("previous_hue_scene", return_direct=True)
def previous_hue_scene():
    """Wechselt zur vorherigen Philips Hue Lichtszene in der aktuellen Gruppe."""
    try:
        run_async(hue_controller.previous_scene())
        return audio_manager.respond_with_audio(SCENE_PREVIOUS_SUCCESS)
    except Exception as e:
        error_msg = f"Fehler beim Wechseln zur vorherigen Lichtszene: {str(e)}"
        return audio_manager.respond_with_audio(error_msg)

# ---- Lichtsteuerung Tools ----

@tool("toggle_hue_lights", return_direct=True)
def toggle_hue_lights(action: str, fade_duration: float = 2.0):
    """Schaltet alle Philips Hue Lichter ein oder aus mit einem sanften Übergang.
    
    Args:
        action: Gewünschte Aktion: 'on' oder 'off'
        fade_duration: Fade-Dauer in Sekunden (optional, Standard: 2.0)
    """
    try:
        if action.lower() == "on":
            run_async(hue_controller.turn_on())
            return audio_manager.respond_with_audio(LIGHT_ON_SUCCESS)
        elif action.lower() == "off":
            run_async(hue_controller.turn_off())
            return audio_manager.respond_with_audio(LIGHT_OFF_SUCCESS)
        else:
            error_msg = f"Ungültige Aktion: '{action}'. Bitte 'on' oder 'off' verwenden."
            return audio_manager.respond_with_audio(error_msg)
    except Exception as e:
        error_msg = f"Fehler beim Schalten der Lichter: {str(e)}"
        return audio_manager.respond_with_audio(error_msg)

@tool("adjust_hue_brightness", return_direct=True)
def adjust_hue_brightness(percent_change: float):
    """Passt die Helligkeit der Philips Hue Lichter prozentual an.
    
    Args:
        percent_change: Prozentuale Änderung der Helligkeit (positiv = heller, negativ = dunkler)
    """
    try:
        run_async(hue_controller.adjust_brightness(percent_change))
        if percent_change > 0:
            response = BRIGHTNESS_ADJUST_INCREASE.format(value=abs(percent_change))
        else:
            response = BRIGHTNESS_ADJUST_DECREASE.format(value=abs(percent_change))
        return audio_manager.respond_with_audio(response)
    except Exception as e:
        error_msg = f"Fehler bei der Helligkeitsanpassung: {str(e)}"
        return audio_manager.respond_with_audio(error_msg)

@tool("set_hue_brightness", return_direct=True)
def set_hue_brightness(percent: int):
    """Setzt die Helligkeit der Philips Hue Lichter auf einen bestimmten Prozentwert.
    
    Args:
        percent: Helligkeit in Prozent (0-100)
    """
    try:
        percent = max(0, min(100, percent))
        run_async(hue_controller.set_brightness(percent))
        response = BRIGHTNESS_SET_SUCCESS.format(percent=percent)
        return audio_manager.respond_with_audio(response)
    except Exception as e:
        error_msg = f"Fehler beim Setzen der Helligkeit: {str(e)}"
        return audio_manager.respond_with_audio(error_msg)

def get_hue_tools():
    return [
        list_hue_scenes,
        activate_hue_scene,
        next_hue_scene,
        previous_hue_scene,
        toggle_hue_lights,
        adjust_hue_brightness,
        set_hue_brightness
    ]