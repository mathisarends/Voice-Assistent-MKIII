import os
import random
from openai import OpenAI

from audio.audio_manager import play

class PhraseGenerator:
    def __init__(self, voice="nova", output_dir="audio/sounds/standard_phrases"):
        self.openai = OpenAI()
        self.voice = voice
        self.output_dir = output_dir
        
        # Verzeichnis existiert bereits, also müssen wir es nicht erstellen
    
    def generate_speech_file(self, text, category="general", file_format="mp3"):
        if not text.strip():
            raise ValueError("Der eingegebene Text ist leer.")
        
        try:
            # Kategorie-Unterverzeichnis erstellen
            category_dir = os.path.join(self.output_dir, category)
            os.makedirs(category_dir, exist_ok=True)
            
            # Nächsten verfügbaren Dateinamen bestimmen
            existing_files = [f for f in os.listdir(category_dir) if f.endswith(f".{file_format}")]
            index = len(existing_files) + 1
            file_name = f"tts_{category}_{index}.{file_format}"
            file_path = os.path.join(category_dir, file_name)
            
            # TTS API aufrufen
            response = self.openai.audio.speech.create(
                model="tts-1",
                voice=self.voice,
                input=text
            )
            
            # Inhalt in Datei schreiben
            with open(file_path, "wb") as file:
                file.write(response.content)
            
            print(f"✅ Sprachdatei gespeichert: {file_path}")
            return file_path
        
        except Exception as e:
            print(f"❌ Fehler bei der Sprachgenerierung: {e}")
            return None

    def play_random_speech_file_from_category(self, category="general"):
        category_dir = os.path.join(self.output_dir, category)
        if not os.path.exists(category_dir):
            print(f"❌ Keine Dateien in der Kategorie '{category}' gefunden.")
            return None

        files = [f for f in os.listdir(category_dir) if f.endswith(".mp3")]
        if not files:
            print(f"❌ Keine gespeicherten Dateien in '{category}'.")
            return None

        # Wähle eine zufällige Datei
        random_file = random.choice(files)
        
        # Entferne die Dateiendung (.mp3)
        file_without_extension = os.path.splitext(random_file)[0]
        
        play(file_without_extension)

if __name__ == "__main__":
    # PhraseGenerator mit dem korrekten Pfad initialisieren
    tts = PhraseGenerator(output_dir="audio/sounds/standard_phrases")
    
    # Wetter
    # tts.generate_speech_file("Analysiere Wetterdaten. Initiiere Wetterprotokoll.", category="weather")
    # tts.generate_speech_file("Scanning meteorologische Datenbanken. Wetter-Update wird vorbereitet.", category="weather")
    # tts.generate_speech_file("Umgebungsparameter werden überprüft. Atmosphärische Bedingungen werden berechnet.", category="weather")
    # tts.generate_speech_file("Standort-Tracking aktiviert. Meteorologische Systeme online.", category="weather")
    # tts.generate_speech_file("Wetter-Informationen werden abgerufen. Präzisionsanalyse läuft.", category="weather")
    # tts.generate_speech_file("Atmosphärische Datenstruktur wird kompiliert. Fortschritt: 25 Prozent", category="weather")
    
    # tts.generate_speech_file("Benutze Licht Workflow.", category="test")
    
    # spotify_phrases = [
    #     "Musikdatenbanken werden abgerufen. Präzisionsanalyse läuft.",
    #     "Audiowiedergabesystem synchronisiert. Musikstreaming-Protokolle initiiert.",
    #     "Soundmanagement wird vorbereitet. Audioressourcen werden gescannt.",
    #     "Musikwiedergabesystem online. Erweiterte Audiosteuerung initiiert."
    # ]
    
    # for phrase in spotify_phrases:
    #     tts.generate_speech_file(phrase, category="spotify_loading")
    
    
    # notion_todo_phrases = [
    #     "Aufgabenstruktur wird kompiliert. Fortschritt: 25 Prozent",
    #     "Produktivitäts-Managementsystem geladen. Aufgabenoptimierung startet.",
    #     "Intelligente Taskverwaltung initiiert. Projektstruktur wird analysiert.",
    #     "To-Do-Algorithmus aktiviert. Aufgabenprioritäten werden berechnet.",
    #     "Projektmanagement-Systeme online. Aufgabenintegritätscheck läuft."
    # ]
    
    # for phrase in notion_todo_phrases:
    #     tts.generate_speech_file(phrase, category="notion_todo_loading")


    # notion_clipboard_phrases = [
    #     "Recherche-Tracking aktiviert. Informationssysteme online.",
    #     "Globale Datenrecherche wird vorbereitet. Wissensakkumulation startet.",
    #     "Informationsretrievalsystem initiiert. Webdatenbank wird gescannt.",
    #     "Intelligente Suchalgorithmen aktiviert. Informationsfilterung läuft.",
    #     "Zwischenablage-Recherchemodul online. Datensammlung wird gestartet."
    # ]   
    
    # for phrase in notion_clipboard_phrases:
    #     tts.generate_speech_file(phrase, category="notion_clipboard_loading")
    
    # lights_phrases = [
    #     "Beleuchtungssysteme werden gescannt.",
    #     "Lichtmanagement wird aktiviert.",
    #     "Farbspektrum wird kalibriert.",
    #     "Lichtsteuerung wird gestartet.",
    #     "Adaptive Lichtanpassung beginnt.",
    #     "Philips Hue wird synchronisiert.",
    #     "Dynamische Lichtanpassung bereit."
    # ]
    
    # for phrase in lights_phrases:
    #     tts.generate_speech_file(phrase, category="lights_loading")
    
    # volume_phrases = [
    #     "Lautstärkesteuerung wird aktiviert.",
    #     "Audiosystem wird angepasst.",
    #     "Lautstärkeregler wird initialisiert.",
    #     "Audioparameter werden konfiguriert.",
    #     "Klangeinstellungen werden geladen.",
    #     "Lautstärkeprofile werden aktualisiert.",
    #     "Audiosystem wird kalibriert.",
    #     "Volumenkontrolle wird vorbereitet."
    # ]
    
    # for phrase in volume_phrases:
    #     tts.generate_speech_file(phrase, category="volume_loading")
    
    # pomodoro_phrases = [
    #         "Ihr Pomodoro-Timer ist abgelaufen. Zeit für eine kleine Unterbrechung.",
    #         "Die Fokuszeit ist vorbei. Eine kurze Pause tut jetzt gut.",
    #         "Pomodoro-Session beendet. Ihr Gehirn freut sich über eine Erholungspause.",
    #         "Die Zeit ist um. Ein guter Moment, kurz durchzuatmen.",
    #         "Iwhre Arbeitsphase ist abgeschlossen. Zeit für einen Moment der Entspannung.",
    #         "Ihr Fokusintervall ist vorüber. Zeit, den Gedanken kurz freien Lauf zu lassen.",
    #         "Die Phase konzentrierten Arbeitens ist vorüber. Lassen Sie Ihre Gedanken kurz wandern.",
    # ]
    
    # for phrase in pomodoro_phrases:
    #     tts.generate_speech_file(phrase, category="pomodoro_phrases")
    
    
    # pomodoro_selection_phrases = [
    #     "Zeitmanagement-Workflow ausgewählt. Pomodoro-Funktionen stehen zur Verfügung.",
    #     "Produktivitäts-Workflow Pomodoro wurde ausgewählt.",
    #     "Pomodoro-Funktionalität steht zur Verfügung.",
    #     "Zeitmanagement mit Pomodoro wird vorbereitet.",
    #     "Pomodoro-Workflow steht Ihnen jetzt zur Verfügung."
    # ]
    
    # for phrase in pomodoro_selection_phrases:
    #     tts.generate_speech_file(phrase, category="pomodoro_Loading")
   
    # alarm_phrases = [
    #     "Weckprotokoll-Parameter werden überprüft. Alarm-Synchronisation wird berechnet.",
    #     "Temporales Weckmodul aktiviert. Aufwachsequenz wird initiiert.",
    #     "Wecker-Systemintegration startet. Intelligente Weckfunktionen werden geladen.",
    #     "Alarm-Präzisionsprotokoll wird vorbereitet. Zeitliche Synchronisation aktiviert.",
    #     "Alarm-Systemintegration online. Adaptive Weckstrategien werden aktiviert.",
    #     "Lichtwecker-Protokoll initiiert. Dynamische Aufwachsteuerung wird vorbereitet."
    # ]
    
    # for phrase in alarm_phrases:
    #     tts.generate_speech_file(phrase, category="alarm_loading")
    
    pomodoro_phrases = [
        "Pomodoro-Timer wird initialisiert.",
        "Fokus-Timing wird aktiviert.",
        "Produktivitäts-Timer wird vorbereitet.",
        "Zeitmanagement-System wird gestartet.",
        "Pomodoro-Protokoll wird geladen.",
        "Arbeitszyklus-Timer wird konfiguriert.",
        "Fokus-Intervallsystem wird bereitgestellt.",
        "Pomodoro-Tracking wird aktiviert."
    ]
    
    for phrase in pomodoro_phrases:
        tts.generate_speech_file(phrase, category="pomodoro_loading")

    

