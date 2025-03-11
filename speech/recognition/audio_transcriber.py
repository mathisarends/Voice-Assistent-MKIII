import time
import os
from openai import OpenAI

class AudioTranscriber:
    def __init__(self):
        self.openai = OpenAI()
        
    def transcribe_audio(self, filename):
        """Sendet die Audiodatei an OpenAI Whisper API und gibt den erkannten Text zurück"""
        print("📝 Sende Audiodatei an OpenAI...")
        
        try:
            start_time = time.time()
            
            with open(filename, "rb") as audio_file:
                transcription = self.openai.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    response_format="text",
                    # prompt="" kann optionale hinzugefügt werden
                )
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"⏱️ API-Antwortzeit: {elapsed_time:.2f} Sekunden")
            print(f"📊 Dateigröße: {os.path.getsize(filename) / 1024:.2f} KB")

            return transcription  
            
        except Exception as e:
            print(f"❌ Fehler bei der Transkription: {str(e)}")
            return None