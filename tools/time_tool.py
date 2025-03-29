import datetime

from langchain.tools import tool


@tool
def get_current_time() -> str:
    """
    Gibt das aktuelle Datum und die aktuelle Uhrzeit in einem menschenlesbaren Format zurück.
    """
    now = datetime.datetime.now()
    return now.strftime("Datum: %Y-%m-%d Uhrzeit: %H:%M:%S")