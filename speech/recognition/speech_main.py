from speech.recognition.audio_transcriber import AudioTranscriber
from speech.recognition.speech_recorder import SpeechRecorder

from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    speech_recorder = SpeechRecorder()
    audio_transcriber = AudioTranscriber()

    filename = speech_recorder.record_audio()

    if filename:
        transcription = audio_transcriber.transcribe_audio(filename)
        if transcription:
            print(f"📝 Erkannter Text: {transcription}")
        else:
            print("❌ Fehler bei der Transkription.")
    else:
        print("❌ Fehler bei der Aufnahme.")
