import asyncio

from langchain.tools import tool

from audio.workflow_audio_response_manager import WorkflowAudioResponseManager
from tools.pomodoro.pomodoro_manager import PomodoroManager

# Konstanten für Pomodoro-Antworten
POMODORO_START_SUCCESS = "Pomodoro-Timer für {duration} Minuten gestartet."
POMODORO_START_FAIL = "Es läuft bereits ein Timer."
POMODORO_START_INVALID = "Die Dauer des Pomodoro-Timers muss positiv sein."
POMODORO_STOP_SUCCESS = "Der Pomodoro-Timer wurde erfolgreich gestoppt."
POMODORO_STOP_FAIL = "Es läuft kein Timer, der gestoppt werden könnte."
POMODORO_STATUS_ACTIVE = "Pomodoro-Timer läuft. Noch {minutes} Minuten verbleibend."
POMODORO_STATUS_INACTIVE = (
    "Kein Pomodoro-Timer aktiv. Du kannst einen neuen Timer starten."
)
POMODORO_RESET = (
    "Pomodoro-Timer wurde zurückgesetzt. Du kannst jetzt einen neuen Timer starten."
)

audio_manager = WorkflowAudioResponseManager(
    category="pomodoro_responses",
)

pomodoro_manager = PomodoroManager()


def run_async(coro):
    return asyncio.run(coro)


@tool(return_direct=True)
def start_pomodoro(duration_minutes: int) -> str:
    """
    Startet einen Pomodoro-Timer für die angegebene Dauer in Minuten.

    Args:
        duration_minutes: Die Dauer des Pomodoro-Timers in Minuten (üblicherweise 25).
    """
    try:
        if duration_minutes <= 0:
            return audio_manager.respond_with_audio(POMODORO_START_INVALID)

        success = pomodoro_manager.start_timer(duration_minutes)

        if success:
            response = POMODORO_START_SUCCESS.format(duration=duration_minutes)
            return audio_manager.respond_with_audio(response)
        else:
            return audio_manager.respond_with_audio(POMODORO_START_FAIL)
    except Exception as e:
        error_msg = f"Fehler beim Starten des Pomodoro-Timers: {str(e)}"
        return audio_manager.respond_with_audio(error_msg)


@tool(return_direct=True)
def stop_pomodoro() -> str:
    """
    Stoppt den aktuell laufenden Pomodoro-Timer.
    """
    try:
        success = pomodoro_manager.stop_timer()

        if success:
            return audio_manager.respond_with_audio(POMODORO_STOP_SUCCESS)
        else:
            return audio_manager.respond_with_audio(POMODORO_STOP_FAIL)
    except Exception as e:
        error_msg = f"Fehler beim Stoppen des Pomodoro-Timers: {str(e)}"
        return audio_manager.respond_with_audio(error_msg)


@tool(return_direct=True)
def get_pomodoro_status() -> str:
    """
    Gibt Informationen über den aktuellen Status des Pomodoro-Timers zurück.
    """
    try:
        remaining_minutes = pomodoro_manager.get_remaining_minutes()

        if remaining_minutes > 0:
            response = POMODORO_STATUS_ACTIVE.format(minutes=remaining_minutes)
            return audio_manager.respond_with_audio(response)
        else:
            return audio_manager.respond_with_audio(POMODORO_STATUS_INACTIVE)
    except Exception as e:
        error_msg = f"Fehler beim Abrufen des Pomodoro-Status: {str(e)}"
        return audio_manager.respond_with_audio(error_msg)


@tool(return_direct=True)
def reset_pomodoro() -> str:
    """
    Stoppt den aktuellen Timer und setzt alle Zustände zurück.
    """
    try:
        pomodoro_manager.stop_timer()
        return audio_manager.respond_with_audio(POMODORO_RESET)
    except Exception as e:
        error_msg = f"Fehler beim Zurücksetzen des Pomodoro-Timers: {str(e)}"
        return audio_manager.respond_with_audio(error_msg)


def get_pomodoro_tools():
    return [start_pomodoro, stop_pomodoro, get_pomodoro_status, reset_pomodoro]
