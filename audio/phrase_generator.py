import os

from openai import OpenAI

from util.decorator import log_exceptions_from_self_logger


class PhraseGenerator:
    def __init__(self, voice="nova", output_dir="audio/sounds/standard_phrases"):
        self.openai = OpenAI()
        self.voice = voice
        self.output_dir = output_dir

    @log_exceptions_from_self_logger(context="Fehler bei der Sprachgenerierung")
    def generate_speech_file(self, text, category="general", file_format="mp3"):
        if not text.strip():
            raise ValueError("Der eingegebene Text ist leer.")

        category_dir = os.path.join(self.output_dir, category)
        os.makedirs(category_dir, exist_ok=True)

        existing_files = [
            f for f in os.listdir(category_dir) if f.endswith(f".{file_format}")
        ]
        index = len(existing_files) + 1
        file_name = f"tts_{category}_{index}.{file_format}"
        file_path = os.path.join(category_dir, file_name)

        response = self.openai.audio.speech.create(
            model="tts-1", voice=self.voice, input=text
        )

        with open(file_path, "wb") as file:
            file.write(response.content)

        print(f"✅ Sprachdatei gespeichert: {file_path}")
        return file_path


if __name__ == "__main__":
    tts = PhraseGenerator(output_dir="audio/sounds/standard_phrases")