import os
import pyaudio
import queue
import time
import threading
import sys
from google.cloud import speech

class SpeechRecognition:
    def __init__(self, credentials_filename="credentials.json", language="de-DE", silence_timeout=5, 
                 alternative_languages=None, speech_contexts=None, model="default"):
        """
        Initialisiert die Spracherkennungsklasse mit erweiterten Konfigurationsoptionen.

        :param credentials_filename: Name der Google Cloud Credential JSON-Datei
        :param language: Primäre Sprache für die Spracherkennung (z. B. "de-DE")
        :param silence_timeout: Zeit in Sekunden ohne erkannte Sprache, bevor die Aufnahme stoppt
        :param alternative_languages: Liste alternativer Sprachen (z.B. ["en-US", "fr-FR"])
        :param speech_contexts: Liste von Wörtern oder Phrasen, die bevorzugt erkannt werden sollen
        :param model: Zu verwendendes Sprachmodell ("default", "command_and_search", "phone_call", "video", ...)
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_path = os.path.join(script_dir, credentials_filename)

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        self.language = language
        self.client = speech.SpeechClient()
        self.audio_queue = queue.Queue()
        self.silence_timeout = silence_timeout

        # Erstelle Speech Contexts für verbesserte Erkennung von spezifischen Begriffen
        speech_contexts_config = []
        if speech_contexts:
            speech_contexts_config = [
                speech.SpeechContext(phrases=speech_contexts, boost=10.0)
            ]

        # Konfiguriere alternative Sprachen falls angegeben
        alternative_language_codes = alternative_languages if alternative_languages else []

        # RecognitionConfig erstellen
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=self.language,
            alternative_language_codes=alternative_language_codes,
            speech_contexts=speech_contexts_config,
            model=model,
            use_enhanced=True,  # Verwende das verbesserte Modell
            profanity_filter=False,  # Keine Filterung von "unanständigen" Wörtern
            enable_automatic_punctuation=True,  # Automatische Interpunktion aktivieren
        )

        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.config, 
            interim_results=True
        )

        self.stop_recording = False

    def _callback(self, in_data, frame_count, time_info, status):
        """Speichert eingehende Audiodaten in der Warteschlange."""
        if not self.stop_recording:
            self.audio_queue.put(in_data)
        return None, pyaudio.paContinue

    def _generate_audio(self):
        """Sendet Audiodaten an Google Speech API."""
        while not self.stop_recording:
            try:
                data = self.audio_queue.get(timeout=0.5)
                yield speech.StreamingRecognizeRequest(audio_content=data)
            except queue.Empty:
                if self.stop_recording:
                    break
                continue
            except Exception as e:
                print(f"Fehler beim Generieren des Audio-Streams: {e}")
                self.stop_recording = True
                break

    def _stop_recording_initial(self):
        """Hilfsmethode für den initialen Timeout."""
        print("⏳ Keine Sprache erkannt, Aufnahme wird gestoppt (initiales Timeout).")
        self.stop_recording = True

    def record_user_prompt(self):
        """
        Startet die Sprachaufnahme und gibt sofort das erste finale Transkript zurück.
        Zeigt Zwischentranskriptionen in Echtzeit an.

        :return: String mit dem erkannten Text oder leerer String, wenn kein finales Ergebnis.
        """
        self.stop_recording = False
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=int(16000 / 10),
            stream_callback=self._callback,
        )

        print("🎤 Starte Aufnahme... Sprich jetzt!")

        # Initialer Timeout für den Fall, dass keine Sprache erkannt wird
        initial_timeout = threading.Timer(self.silence_timeout, self._stop_recording_initial)
        initial_timeout.daemon = True
        initial_timeout.start()
        
        # Variable zum Tracken des finalen Ergebnisses
        final_transcript = ""
        
        try:
            responses = self.client.streaming_recognize(
                self.streaming_config, 
                self._generate_audio()
            )
            
            last_speech_time = time.time()

            for response in responses:
                # Timer deaktivieren, sobald wir in der Schleife sind
                if initial_timeout.is_alive():
                    initial_timeout.cancel()
                
                if self.stop_recording:
                    break
                
                if not response.results:
                    continue

                for result in response.results:
                    # Bei finalem Ergebnis sofort zurückgeben
                    if result.is_final:
                        final_transcript = result.alternatives[0].transcript
                        print(f"\n📝 Finale Transkription: {final_transcript}")
                        
                        # Optional: Alternative Transkriptionen anzeigen
                        if len(result.alternatives) > 1:
                            print("🔄 Alternative Transkriptionen:")
                            for i, alternative in enumerate(result.alternatives[1:], 1):
                                print(f"  {i}. {alternative.transcript}")
                        
                        self.stop_recording = True
                        break  # Schleife beenden
                    else:
                        # Zwischentranskription anzeigen
                        transcript = result.alternatives[0].transcript
                        print(f"\r🔄 Zwischentranskription: {transcript}", end="", flush=True)
                        last_speech_time = time.time()
                
                # Wenn wir ein finales Ergebnis haben, brechen wir die Schleife ab
                if self.stop_recording and final_transcript:
                    break
                
                # Timeout prüfen
                if time.time() - last_speech_time > self.silence_timeout:
                    print("\n⏳ Keine weitere Sprache erkannt, Aufnahme wird gestoppt.")
                    self.stop_recording = True
                    break
                
        except Exception as e:
            print(f"\nFehler während der Spracherkennung: {e}")
        finally:
            # Aufräumen
            if initial_timeout.is_alive():
                initial_timeout.cancel()
            
            try:
                stream.stop_stream()
            except OSError:
                pass
            
            try:
                stream.close()
            except OSError:
                pass
            
            try:
                p.terminate()
            except OSError:
                pass
            
            print("\n✅ Aufnahme beendet.")

        # Rückgabe des finalen Transkripts, wenn vorhanden
        return final_transcript


if __name__ == "__main__":
    # Beispielkonfiguration für verbesserte Erkennung technischer Begriffe
    tech_phrases = [
        "Langchain", "ChatGPT", "Python", "API", "LLM", 
        "Machine Learning", "AI", "Künstliche Intelligenz",
        "Prompt Engineering", "Transformer", "OpenAI", "Claude",
        "Anthropic", "Embedding", "Vector Database"
    ]
    
    # Erstelle eine Instanz mit Deutsch als Hauptsprache und Englisch als Alternative
    recorder = SpeechRecognition(
        language="de-DE",
        alternative_languages=["en-US"],  # Englisch als alternative Sprache
        speech_contexts=tech_phrases,  # Technische Begriffe bevorzugen
        model="default",  # Alternatives Modell: "command_and_search" für kurze Sprachbefehle
        silence_timeout=3
    )
    
    try:
        print("Das Programm startet in 3 Sekunden...")
        time.sleep(3)
        print("Fang an zu sprechen!")
        
        start_time = time.time()
        user_text = recorder.record_user_prompt()
        end_time = time.time()
        
        duration = end_time - start_time
        
        if user_text:
            print(f"\n🎤 Endgültiges Ergebnis: {user_text}")
        else:
            print("\n⚠️ Keine finale Transkription erhalten.")
        
        print(f"Verstrichene Zeit: {duration:.2f} Sekunden")
    except KeyboardInterrupt:
        print("\n\nProgramm durch Benutzer beendet (Ctrl+C).")
        sys.exit(0)