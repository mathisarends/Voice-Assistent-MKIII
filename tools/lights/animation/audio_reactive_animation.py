from __future__ import annotations

import asyncio
import math
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pyaudio
from scipy.fft import fft

from tools.lights.bridge.bridge import HueBridge
from tools.lights.light_controller import LightController
from util.loggin_mixin import LoggingMixin


class AudioCapture(LoggingMixin):
    """Klasse zur Audioaufnahme und Analyse"""

    def __init__(
        self,
        chunk_size: int = 1024,
        sample_rate: int = 44100,
        history_size: int = 5,
        smoothing_factor: float = 0.3,
    ):
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.running = False
        self.thread = None

        # Frequenzbereiche für Analyse
        self.freq_bins = {
            "bass": (20, 250),  # Tiefe Frequenzen (Bass)
            "mid": (250, 2000),  # Mittlere Frequenzen
            "high": (2000, 10000),  # Hohe Frequenzen
        }

        # Für Glättung der Werte
        self.history = {band: deque(maxlen=history_size) for band in self.freq_bins}
        self.energy_levels = {band: 0.0 for band in self.freq_bins}
        self.smoothing_factor = smoothing_factor

        # Für Erkennung von Beats
        self.beat_threshold = 1.5
        self.beat_detected = {band: False for band in self.freq_bins}
        self.last_beat_time = {band: 0 for band in self.freq_bins}

        # Zur Normalisierung
        self.energy_max = {
            band: 0.1 for band in self.freq_bins
        }  # Anfangswert um Division durch Null zu vermeiden
        self.energy_min = {band: 0.0 for band in self.freq_bins}
        self.auto_gain_control = True

    def start(self) -> None:
        """Startet die Audioaufnahme in einem separaten Thread"""
        if self.running:
            return

        self.stream = self.audio.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
        )

        self.running = True
        self.thread = threading.Thread(target=self._audio_processing_loop)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("Audioaufnahme gestartet")

    def stop(self) -> None:
        """Stoppt die Audioaufnahme"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        self.logger.info("Audioaufnahme gestoppt")

    def _audio_processing_loop(self) -> None:
        """Kontinuierliche Verarbeitung des Audioeingangs"""
        try:
            while self.running:
                if self.stream:
                    audio_data = self.stream.read(
                        self.chunk_size, exception_on_overflow=False
                    )
                    self._analyze_audio(audio_data)
        except Exception as e:
            self.logger.error(f"Fehler bei der Audioverarbeitung: {e}")
            self.running = False

    def _analyze_audio(self, audio_data: bytes) -> None:
        """Analysiert die Audiodaten und extrahiert Frequenzmerkmale"""
        try:
            # Konvertiere Bytes zu Numpy-Array
            audio_array = np.frombuffer(audio_data, dtype=np.float32)

            # Anwenden eines Fensters zur Vermeidung von spektralem Leck
            window = np.hanning(len(audio_array))
            audio_array = audio_array * window

            # FFT berechnen
            fft_result = fft(audio_array)
            magnitude = np.abs(fft_result[: len(audio_array) // 2])

            # Frequenzskala
            freqs = np.fft.fftfreq(len(audio_array), 1.0 / self.sample_rate)
            freqs = freqs[: len(audio_array) // 2]

            # Berechne Energie in den verschiedenen Frequenzbändern
            current_time = (
                time.time()
            )  # Verwende time.time() statt asyncio.get_event_loop().time()

            for band, (low_freq, high_freq) in self.freq_bins.items():
                # Indizes für die Frequenzbereiche
                low_idx = np.argmax(freqs >= low_freq) if any(freqs >= low_freq) else 0
                high_idx = (
                    np.argmax(freqs >= high_freq)
                    if any(freqs >= high_freq)
                    else len(freqs) - 1
                )

                # Energie in diesem Band
                band_energy = np.mean(magnitude[low_idx:high_idx])
                self.history[band].append(band_energy)

                # Aktualisiere Min/Max für Normalisierung
                if self.auto_gain_control:
                    self.energy_max[band] = max(self.energy_max[band], band_energy)
                    # Langsames Absinken des Maximums, um auf Änderungen zu reagieren
                    self.energy_max[band] *= 0.9999

                # Glatte Energiewerte mit einem einfachen EMA (Exponential Moving Average)
                if len(self.history[band]) > 0:
                    avg_energy = sum(self.history[band]) / len(self.history[band])
                    self.energy_levels[band] = (
                        self.smoothing_factor * band_energy
                        + (1 - self.smoothing_factor) * self.energy_levels[band]
                    )

                # Beat-Erkennung (einfacher Schwellenwert-basierter Ansatz)
                avg_history = (
                    sum(self.history[band]) / len(self.history[band])
                    if self.history[band]
                    else 0
                )
                if (
                    band_energy > self.beat_threshold * avg_history
                    and current_time - self.last_beat_time[band] > 0.1
                ):  # Mindestens 100ms zwischen Beats
                    self.beat_detected[band] = True
                    self.last_beat_time[band] = current_time
                else:
                    self.beat_detected[band] = False

        except Exception as e:
            self.logger.error(f"Fehler bei der Audioanalyse: {e}")

    def get_energy_normalized(self, band: str) -> float:
        """Gibt den normalisierten Energiewert (0-1) für ein Frequenzband zurück"""
        if band not in self.energy_levels:
            return 0.0

        if self.energy_max[band] == self.energy_min[band]:
            return 0.0

        value = (self.energy_levels[band] - self.energy_min[band]) / (
            self.energy_max[band] - self.energy_min[band]
        )
        return max(0.0, min(1.0, value))  # Begrenze auf 0-1

    def is_beat(self, band: str) -> bool:
        """Prüft, ob in einem bestimmten Frequenzband ein Beat erkannt wurde"""
        return self.beat_detected.get(band, False)

    def get_all_levels(self) -> Dict[str, float]:
        """Gibt alle normalisierten Energiewerte für alle Bänder zurück"""
        return {band: self.get_energy_normalized(band) for band in self.freq_bins}

    def get_all_beats(self) -> Dict[str, bool]:
        """Gibt den Beat-Status für alle Bänder zurück"""
        return {band: self.is_beat(band) for band in self.freq_bins}


class AudioReactiveAnimation(LoggingMixin):
    """Basisklasse für audio-reaktive Lichtanimationen"""

    def __init__(self, controller: LightController, audio_capture: AudioCapture = None):
        self.controller = controller
        self.audio_capture = audio_capture or AudioCapture()
        self._stop_event = asyncio.Event()
        self._running_task: Optional[asyncio.Task] = None
        self._update_interval = 0.05  # 50 ms Standardintervall (20 Hz)

    async def start(self, light_ids: List[str], **kwargs) -> None:
        """
        Startet die audio-reaktive Animation

        Args:
            light_ids: Liste der Lampen-IDs
            **kwargs: Zusätzliche Parameter für die Animation
        """
        # Stoppe eventuell laufende Animation
        await self.stop()

        # Setze das Stop-Event zurück
        self._stop_event.clear()

        # Starte die Audioaufnahme, falls noch nicht geschehen
        if not self.audio_capture.running:
            self.audio_capture.start()

        # Starte die Animation-Loop
        self._running_task = asyncio.create_task(
            self._animation_loop(light_ids, **kwargs)
        )

        self.logger.info(f"Audio-reaktive Animation für Lampen {light_ids} gestartet")

    async def stop(self) -> None:
        """Stoppt die audio-reaktive Animation"""
        if self._running_task and not self._running_task.done():
            self._stop_event.set()
            try:
                await self._running_task
            except asyncio.CancelledError:
                pass
            self._running_task = None

        # Audioaufnahme wird nicht automatisch gestoppt, kann von mehreren Animationen genutzt werden

        self.logger.info("Audio-reaktive Animation gestoppt")

    @abstractmethod
    async def _process_audio_frame(
        self,
        light_ids: List[str],
        audio_levels: Dict[str, float],
        beats: Dict[str, bool],
        **kwargs,
    ) -> None:
        """
        Verarbeitet ein Audio-Frame und aktualisiert die Lampen entsprechend

        Args:
            light_ids: Liste der Lampen-IDs
            audio_levels: Normalisierte Energiewerte pro Frequenzband (0-1)
            beats: Beat-Erkennungsstatus pro Frequenzband
            **kwargs: Zusätzliche Parameter für die Animation
        """
        pass

    async def _animation_loop(self, light_ids: List[str], **kwargs) -> None:
        """Hauptschleife für die Animation"""
        try:
            while not self._stop_event.is_set():
                # Hole aktuelle Audio-Daten
                audio_levels = self.audio_capture.get_all_levels()
                beats = self.audio_capture.get_all_beats()

                # Aktualisiere Lichter basierend auf Audio
                await self._process_audio_frame(
                    light_ids, audio_levels, beats, **kwargs
                )

                # Warte kurz für das nächste Update
                await asyncio.sleep(self._update_interval)
        except Exception as e:
            self.logger.error(f"Fehler in der Audio-Animation-Loop: {e}")
        finally:
            self.logger.info("Audio-Animation-Loop beendet")


class BeatPulseAnimation(AudioReactiveAnimation):
    """Animation, die Lichter im Takt der Musik pulsieren lässt"""

    async def _process_audio_frame(
        self,
        light_ids: List[str],
        audio_levels: Dict[str, float],
        beats: Dict[str, bool],
        color_mode: str = "bass",
        brightness_mode: str = "energy",
        intensity: float = 1.0,
        color_shift: bool = True,
        **kwargs,
    ) -> None:
        """
        Verarbeitet Audio-Daten und lässt Lichter im Takt pulsieren

        Args:
            light_ids: Liste der Lampen-IDs
            audio_levels: Normalisierte Energiewerte pro Frequenzband (0-1)
            beats: Beat-Erkennungsstatus pro Frequenzband
            color_mode: Frequenzband für Farbauswahl ('bass', 'mid', 'high')
            brightness_mode: Modus für Helligkeitssteuerung ('energy' oder 'beat')
            intensity: Intensität der Animation (0.0-1.0)
            color_shift: Wenn True, wird die Farbe basierend auf dem Frequenzspektrum verschoben
            **kwargs: Weitere Parameter
        """
        if not light_ids:
            return

        # Parameter prüfen
        color_mode = color_mode if color_mode in audio_levels else "bass"
        brightness_mode = (
            brightness_mode if brightness_mode in ["energy", "beat"] else "energy"
        )

        tasks = []
        for light_id in light_ids:
            # Farbberechnung basierend auf Frequenzspektrum
            hue = 0
            if color_shift:
                # Bass -> Rot, Mitten -> Grün, Höhen -> Blau
                bass_contrib = audio_levels["bass"] * 0
                mid_contrib = audio_levels["mid"] * 25000
                high_contrib = audio_levels["high"] * 46000
                hue = int(bass_contrib + mid_contrib + high_contrib) % 65536

            # Helligkeitsberechnung
            brightness = 0
            if brightness_mode == "energy":
                # Baue eine gewichtete Summe der Energiewerte
                brightness_value = (
                    audio_levels["bass"] * 0.5
                    + audio_levels["mid"] * 0.3
                    + audio_levels["high"] * 0.2
                )
                brightness = int(
                    70 + 185 * brightness_value * intensity
                )  # 70-255 Range
            else:  # 'beat' Modus
                # Verwende Beats für abrupte Helligkeitsänderungen
                if beats[color_mode]:
                    brightness = 254  # Volle Helligkeit bei Beat
                else:
                    energy = audio_levels[color_mode]
                    brightness = int(
                        70 + 100 * energy * intensity
                    )  # Gedämpfte Helligkeit ohne Beat

            # Lichtzustand vorbereiten
            state = {
                "hue": hue,
                "sat": 254,  # Volle Sättigung für lebhafte Farben
                "bri": brightness,
                "transitiontime": 1,  # Kurze Übergangszeit für schnelle Reaktion
            }

            tasks.append(self.controller.set_light_state(light_id, state))

        if tasks:
            await asyncio.gather(*tasks)


# Beispiel für die Verwendung
async def main() -> None:
    bridge = HueBridge.connect_by_ip()
    controller = LightController(bridge)

    # Initialisiere AudioCapture (kann von mehreren Animationen geteilt werden)
    audio_capture = AudioCapture()

    # Beispiel 1: Beat-Pulsation
    print("Starte Beat-Pulsation...")
    beat_animation = BeatPulseAnimation(controller, audio_capture)
    await beat_animation.start(
        ["5", "6", "7"],
        color_mode="bass",
        brightness_mode="energy",
        intensity=0.8,
        color_shift=True,
    )

    # Warte 30 Sekunden
    print("Animation läuft für 30 Sekunden...")
    await asyncio.sleep(30)

    # Stoppe die Animation
    print("Stoppe Animation...")
    await beat_animation.stop()

    # Warte 30 Sekunden
    print("Animation läuft für 30 Sekunden...")
    await asyncio.sleep(30)

    # Stoppe die Audioaufnahme, wenn alle Animationen beendet sind
    audio_capture.stop()


if __name__ == "__main__":
    asyncio.run(main())
