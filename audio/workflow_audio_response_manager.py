import os

from audio.strategy.audio_manager import get_audio_manager
from service.tts_generator import get_tts_generator
from util.decorator import log_exceptions_from_self_logger
from util.loggin_mixin import LoggingMixin


class WorkflowAudioResponseManager(LoggingMixin):
    def __init__(
        self,
        voice="nova",
        category="light_responses",
        output_dir="audio/sounds/standard_phrases",
    ):
        """
        Initialisiert den WorkflowAudioResponseManager.
        """
        self.voice = voice
        self.category = category
        self.output_dir = output_dir

        self.tts_generator = get_tts_generator()
        self.audio_manager = get_audio_manager()

        category_path = os.path.join(output_dir, category)
        self.tts_generator.set_category_path(category, category_path)

        self.tts_generator.load_existing_cache(category)

        self.logger.info(
            f"WorkflowAudioResponseManager initialisiert mit Stimme '{voice}', "
            f"Kategorie '{category}' und Ausgabeverzeichnis '{output_dir}'"
        )

    @log_exceptions_from_self_logger("beim Abspielen der Audioantwort")
    def play_response(self, message: str) -> str:
        """
        Generiert und spielt eine Audioantwort für die Nachricht ab.
        """
        if not message or not message.strip():
            return message

        sound_id = self.tts_generator.generate_tts(message, self.category, self.voice)

        if sound_id:
            self.audio_manager.play(sound_id)

        return message

    def respond_with_audio(self, message: str) -> str:
        """Alias für play_response."""
        return self.play_response(message)
