import os
from typing import List, Optional

import aiofiles
from openai import AsyncOpenAI

from util.decorator import measure_performance
from util.loggin_mixin import LoggingMixin


class AudioTranscriber(LoggingMixin):
    def __init__(self):
        super().__init__()
        self.openai = AsyncOpenAI()

    @measure_performance
    async def transcribe_audio(
        self, filename, language="de", vocabulary: List[str] = ["Wetter"]
    ) -> Optional[str]:
        """
        Sendet die Audiodatei an OpenAI Whisper API und gibt den erkannten Text zurück
        """
        self.logger.info("📝 Sende Audiodatei an OpenAI...")

        try:
            file_basename = os.path.basename(filename)

            prompt = ""
            if language == "de":
                prompt = "Dies ist eine Aufnahme auf Deutsch. "
                
            vocab_str = ", ".join(vocabulary)
            prompt += f"Folgende Wörter können vorkommen: {vocab_str}"

            async with aiofiles.open(filename, "rb") as audio_file:
                audio_data = await audio_file.read()
                
            transcription = await self.openai.audio.transcriptions.create(
                model="whisper-1",
                file=(file_basename, audio_data),
                response_format="text",
                prompt=prompt if prompt else None,
            )

            return transcription

        except Exception as e:
            self.logger.error(f"❌ Fehler bei der Transkription: {str(e)}")
            return None