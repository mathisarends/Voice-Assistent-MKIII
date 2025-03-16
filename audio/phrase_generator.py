import os
import random
from openai import OpenAI

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

    def get_random_speech_file(self, category="general"):
        """Wählt zufällig eine gespeicherte Sprachdatei aus einer Kategorie aus."""
        category_dir = os.path.join(self.output_dir, category)
        if not os.path.exists(category_dir):
            print(f"❌ Keine Dateien in der Kategorie '{category}' gefunden.")
            return None

        files = [f for f in os.listdir(category_dir) if f.endswith(".mp3")]
        if not files:
            print(f"❌ Keine gespeicherten Dateien in '{category}'.")
            return None

        return os.path.join(category_dir, random.choice(files))


if __name__ == "__main__":
    # PhraseGenerator mit dem korrekten Pfad initialisieren
    tts = PhraseGenerator(output_dir="audio/sounds/standard_phrases")
    
    for i in range(0, 105, 5):
        print(i)