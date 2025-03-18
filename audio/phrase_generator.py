import os
import random
from openai import OpenAI

from audio.audio_manager import play

class PhraseGenerator:
    def __init__(self, voice="nova", output_dir="audio/sounds/standard_phrases"):
        """Initialisiert den TTS-Dateigenerator mit OpenAI API und definiert das Ausgabe-Verzeichnis."""
        self.openai = OpenAI()
        self.voice = voice
        self.output_dir = output_dir
        
        # Verzeichnis existiert bereits, also müssen wir es nicht erstellen
    
    def generate_speech_file(self, text, category="general", file_format="mp3"):
        """Erstellt eine Sprachdatei aus dem gegebenen Text und speichert sie im entsprechenden Unterordner."""
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
        """Wählt zufällig eine gespeicherte Sprachdatei aus einer Kategorie aus und gibt nur den Dateinamen ohne Endung zurück."""
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
    
    # tts.generate_speech_file("Analysiere Wetterdaten. Initiiere Wetterprotokoll.", category="weather")
    # tts.generate_speech_file("Scanning meteorologische Datenbanken. Wetter-Update wird vorbereitet.", category="weather")
    # tts.generate_speech_file("Umgebungsparameter werden überprüft. Atmosphärische Bedingungen werden berechnet.", category="weather")
    # tts.generate_speech_file("Standort-Tracking aktiviert. Meteorologische Systeme online.", category="weather")
    # tts.generate_speech_file("Wetter-Informationen werden abgerufen. Präzisionsanalyse läuft.", category="weather")
    # tts.generate_speech_file("Atmosphärische Datenstruktur wird kompiliert. Fortschritt: 25 Prozent", category="weather")
    
    # Workflow related
    # tts.generate_speech_file("Licht-Workflow aktiviert.", category="lights")
    # tts.generate_speech_file("Schalte auf Lichtsteuerung.", category="lights")
    # tts.generate_speech_file("Philips Hue wird angesprochen.", category="lights")
    
    # # Alarm Workflow
    # tts.generate_speech_file("Wecker-Workflow steht bereit.", category="alarm")
    # tts.generate_speech_file("Alarm-Modus aktiviert.", category="alarm")
    # tts.generate_speech_file("Weckzeit wird eingestellt.", category="alarm")
    # tts.generate_speech_file("Alarm-System ist online.", category="alarm")
    # tts.generate_speech_file("Lichtwecker wird konfiguriert.", category="alarm")
    
    # # Weather Workflow

    
    # # Time Tool
    # tts.generate_speech_file("Zeitangabe wird vorbereitet.", category="time")
    # tts.generate_speech_file("Datum und Uhrzeit werden abgerufen.", category="time")
    
    # # Spotify Workflow
    # tts.generate_speech_file("Spotify-Steuerung aktiviert.", category="spotify")
    # tts.generate_speech_file("Spotify-Workflow bereit.", category="spotify")
    # tts.generate_speech_file("Audio-Stream wird konfiguriert.", category="spotify")
    
    # # Notion Todo Workflow
    # tts.generate_speech_file("Todo-Workflow aktiviert.", category="notion_todo")
    # tts.generate_speech_file("Aufgabenmanagement läuft.", category="notion_todo")
    # tts.generate_speech_file("Notion-Tasks werden geladen.", category="notion_todo")
    
    # # Notion Clipboard Workflow
    # tts.generate_speech_file("Recherche-Modus aktiviert.", category="notion_clipboard")
    # tts.generate_speech_file("Clipboard-Workflow bereit.", category="notion_clipboard")
    # tts.generate_speech_file("Recherche-Tool gestartet.", category="notion_clipboard")
    # tts.generate_speech_file("Datensammlung aktiviert.", category="notion_clipboard")
    
    # # Volume Control Workflow
    # tts.generate_speech_file("Lautstärke-Modul aktiviert.", category="volume")
    # tts.generate_speech_file("Audio-Level wird angepasst.", category="volume")
    # tts.generate_speech_file("Sound-Steuerung bereit.", category="volume")
    # tts.generate_speech_file("Volume-Control aktiv.", category="volume")
    # tts.generate_speech_file("Lautstärkeregelung übernommen.", category="volume")
    