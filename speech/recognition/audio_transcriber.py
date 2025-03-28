import time
import os
from typing import Optional
import aiofiles
from openai import AsyncOpenAI


class AudioTranscriber:
    def __init__(self):
        self.openai = AsyncOpenAI()

    async def transcribe_audio(
        self, filename, vocabulary=None, language="de"
    ) -> Optional[str]:
        """Sendet die Audiodatei an OpenAI Whisper API und gibt den erkannten Text zurück"""
        print("📝 Sende Audiodatei an OpenAI...")

        try:
            start_time = time.time()

            file_basename = os.path.basename(filename)

            prompt = ""
            if language == "de":
                prompt = "Dies ist eine Aufnahme auf Deutsch. "

            if vocabulary:
                if isinstance(vocabulary, list):
                    vocab_str = ", ".join(vocabulary)
                else:
                    vocab_str = vocabulary
                prompt += f"Folgende Begriffe könnten vorkommen: {vocab_str}"

            async with aiofiles.open(filename, "rb") as audio_file:
                audio_data = await audio_file.read()

            transcription = await self.openai.audio.transcriptions.create(
                model="whisper-1",
                file=(file_basename, audio_data),
                response_format="text",
                prompt=prompt if prompt else None,
            )

            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"⏱️ API-Antwortzeit: {elapsed_time:.2f} Sekunden")
            print(f"📊 Dateigröße: {os.path.getsize(filename) / 1024:.2f} KB")

            return transcription

        except Exception as e:
            print(f"❌ Fehler bei der Transkription: {str(e)}")
            return None
