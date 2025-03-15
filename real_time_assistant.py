"""
Module for interfacing with OpenAI's Realtime API for voice conversations.
With improved inactivity detection to end conversations after period of silence.
"""
import base64
import asyncio
import logging
import time
import re
from typing import Optional, Dict, Any, cast

import sounddevice as sd
import numpy as np
from openai import AsyncOpenAI
from openai.types.beta.realtime.session import Session
from openai.resources.beta.realtime.realtime import AsyncRealtimeConnection

from audio.audio_player_async import AudioPlayerAsync

# Audio configuration
SAMPLE_RATE = 24000
CHANNELS = 1
READ_SIZE = int(SAMPLE_RATE * 0.02)  # 20ms chunks

class RealtimeAssistant:
    """
    Class for handling real-time voice conversations with OpenAI API.
    This creates a continuous conversation where audio can be streamed
    in real-time both to and from the API.
    """
    
    def __init__(self, inactivity_timeout=15):
        """
        Initialize the realtime assistant.
        
        Args:
            inactivity_timeout: Number of seconds of silence after model response
                               before ending the conversation (default: 15)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # OpenAI client
        self.client = AsyncOpenAI()
        
        # Audio handling
        self.audio_player = AudioPlayerAsync()
        
        # State management
        self.connection: Optional[AsyncRealtimeConnection] = None
        self.session: Optional[Session] = None
        self.is_active = False
        self.should_send_audio = asyncio.Event()
        self.connected = asyncio.Event()
        self.last_audio_item_id = None
        
        # Transcript items
        self.transcript_items: Dict[str, str] = {}
        
        # Inactivity timeout settings
        self.inactivity_timeout = inactivity_timeout
        self.inactivity_timer = None
        self.speaking_timer = None
        self.model_is_responding = False
        self.last_model_audio_time = 0
        
        # Monitor task for detecting end of model response
        self.response_monitor_task = None
    
    async def start_conversation(self):
        """Start a new conversation with OpenAI Realtime API."""
        if self.is_active:
            self.logger.warning("Conversation is already active")
            return
            
        self.logger.info("Starting new conversation")
        self.is_active = True
        
        # Reset state
        self.model_is_responding = False
        self.last_model_audio_time = 0
        
        # Cancel any existing timers
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
            self.inactivity_timer = None
            
        if self.speaking_timer:
            self.speaking_timer.cancel()
            self.speaking_timer = None
            
        if self.response_monitor_task:
            self.response_monitor_task.cancel()
            self.response_monitor_task = None
        
        # Start the monitor for model responses
        self.response_monitor_task = asyncio.create_task(self._monitor_model_responses())
        
        # Start the connection and audio workers
        asyncio.create_task(self._handle_realtime_connection())
        asyncio.create_task(self._process_audio_input())
    
    async def end_conversation(self):
        """End the current conversation."""
        if not self.is_active:
            return
            
        self.logger.info("Ending conversation")
        
        # Stop sending audio
        self.should_send_audio.clear()
        
        # Cancel timers
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
            self.inactivity_timer = None
            
        if self.speaking_timer:
            self.speaking_timer.cancel()
            self.speaking_timer = None
            
        if self.response_monitor_task:
            self.response_monitor_task.cancel()
            self.response_monitor_task = None
        
        # Close the connection if it exists
        if self.connection:
            try:
                await self.connection.close()
            except Exception as e:
                self.logger.error("Error closing connection: %s", e)
            
        self.connection = None
        self.session = None
        self.is_active = False
        self.connected.clear()
        self.transcript_items = {}
    
    async def cancel_current_interaction(self):
        """Cancel the current interaction but keep the connection open."""
        if not self.is_active or not self.connection:
            return
            
        self.logger.info("Canceling current interaction")
        
        # Stop sending audio
        self.should_send_audio.clear()
        
        # Send a cancel message
        try:
            await self.connection.send({"type": "response.cancel"})
            self.logger.info("Sent cancellation signal")
        except Exception as e:
            self.logger.error("Error sending cancellation: %s", e)
    
    def calculate_speaking_duration(self, text):
        """
        Berechnet die geschätzte Sprechdauer für einen gegebenen Text.

        Args:
            text: Der zu sprechende Text.

        Returns:
            float: Geschätzte Sprechdauer in Sekunden.
        """
        if not text.strip():
            return 1.0  # Falls leerer Text, minimale Dauer von 1 Sekunde zurückgeben
        
        # Satzzeichen entfernen, die keine Pausen verursachen
        cleaned_text = re.sub(r'[\"\'\(\)\[\]\{\}]', '', text)

        # Satzzeichen, die eine Pause auslösen (Punkt, Komma, Gedankenstrich etc.)
        sentence_endings = re.findall(r'[.!?;:,]', text)
        pause_duration = len(sentence_endings) * np.random.uniform(0.1, 0.4)  # Kürzere Pausen: 100-400ms

        # Wortanzahl bestimmen
        words = cleaned_text.split()
        word_count = len(words)

        # Dynamische Sprechraten (schnell: 4.5 wps, langsam: 2.5 wps)
        words_per_second = np.random.uniform(2.5, 4.5)  # Schnellere Sprechweise

        # Basisdauer berechnen
        duration = word_count / words_per_second

        # Längere Wörter leicht beeinflussen (erst ab 7 Buchstaben)
        avg_word_length = np.mean([len(word) for word in words]) if words else 5
        duration += max(0, (avg_word_length - 7) * 0.015)  # Minimaler Einfluss

        # Pausenzeit hinzufügen
        duration += pause_duration

        # Absolute Mindestdauer setzen
        duration = max(duration, 0.8)

        self.logger.info(f"Berechnete Sprechdauer für {word_count} Wörter: {duration:.2f} Sekunden")
        
        return duration
    
    async def _wait_for_speaking_completion(self, duration):
        """
        Wait for the model to finish speaking and then start the inactivity timer.
        
        Args:
            duration: Estimated speaking duration in seconds
        """
        self.logger.info(f"Waiting {duration:.2f} seconds for model to finish speaking")
        try:
            # Wait for the calculated speaking duration
            await asyncio.sleep(duration)
            
            # Model has finished speaking, start the inactivity timer
            self.logger.info("Speaking timer completed, starting inactivity timer")
            self.model_is_responding = False
            await self._start_inactivity_timer()
        except asyncio.CancelledError:
            # Timer was cancelled
            pass
    
    async def _monitor_model_responses(self):
        """Monitor when the model is responding and detect when it stops."""
        try:
            while self.is_active:
                if self.model_is_responding and not self.speaking_timer:
                    # Check if model has stopped responding
                    current_time = time.time()
                    time_since_last_audio = current_time - self.last_model_audio_time
                    
                    if time_since_last_audio > 1.0:  # 1 second without audio means model likely stopped
                        self.logger.info("Detected end of model response (no audio for 1 second)")
                        self.model_is_responding = False
                        
                        # Start the inactivity timer
                        await self._start_inactivity_timer()
                
                await asyncio.sleep(0.5)  # Check every 500ms
        except asyncio.CancelledError:
            # Task was cancelled, clean exit
            pass
        except Exception as e:
            self.logger.error(f"Error in model response monitor: {e}")
    
    async def _start_inactivity_timer(self):
        """Start a timer that will end the conversation after inactivity."""
        # Cancel any existing timer
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
        
        # Create a new timer
        self.inactivity_timer = asyncio.create_task(self._inactivity_timeout_handler())
    
    async def _inactivity_timeout_handler(self):
        """Handle inactivity timeout - end the conversation after specified time."""
        self.logger.info(f"Starting inactivity timer ({self.inactivity_timeout} seconds)")
        try:
            # Wait for the timeout period
            await asyncio.sleep(self.inactivity_timeout)
            
            # If we get here, the timer wasn't cancelled, which means there was no activity
            self.logger.info(f"No user activity for {self.inactivity_timeout} seconds after model response, ending conversation")
            await self.end_conversation()
        except asyncio.CancelledError:
            # Timer was cancelled because of user activity
            self.logger.info("Inactivity timer cancelled")
    
    async def _handle_realtime_connection(self):
        """Establish and handle the connection with OpenAI Realtime API."""
        if not self.is_active:
            return
        
        self.logger.info("Establishing connection to OpenAI Realtime API")
        
        async with self.client.beta.realtime.connect(model="gpt-4o-mini-realtime-preview") as conn:
            self.connection = conn
            self.connected.set()
            
            await conn.session.update(session={
                "turn_detection": {"type": "server_vad"},
                "voice": "echo",
                "instructions": "Du bist ein hilfreicher Sprachassistent. Antworte primär auf Deutsch, es sei denn, der Benutzer stellt eine Frage in einer anderen Sprache. Gib kurze, präzise und informative Antworten. Sprich natürlich und freundlich, als ob du mit einem Menschen sprichst."
            })
            
            # Start sending audio immediately
            self.should_send_audio.set()
            
            # Process events from the connection
            async for event in conn:
                if not self.is_active:
                    break
                    
                if event.type == "session.created":
                    self.session = event.session
                    self.logger.info("Session created: %s", event.session.id)
                    
                elif event.type == "session.updated":
                    self.session = event.session
                    
                elif event.type == "response.audio.delta":
                    # Update the last audio time
                    self.last_model_audio_time = time.time()
                    
                    # Model is responding
                    if not self.model_is_responding:
                        self.model_is_responding = True
                        self.logger.info("Model started responding")
                        
                        # Cancel inactivity timer if it exists while model is speaking
                        if self.inactivity_timer:
                            self.inactivity_timer.cancel()
                            self.inactivity_timer = None
                    
                    # Handle audio response from the assistant
                    if event.item_id != self.last_audio_item_id:
                        self.audio_player.reset_frame_count()
                        self.last_audio_item_id = event.item_id
                        
                    bytes_data = base64.b64decode(event.delta)
                    self.audio_player.add_data(bytes_data)
                    
                elif event.type == "response.audio_transcript.delta":
                    # Handle text transcript of the assistant's audio response
                    if event.item_id in self.transcript_items:
                        self.transcript_items[event.item_id] += event.delta
                    else:
                        self.transcript_items[event.item_id] = event.delta
                        
                    # Print the full current transcript for this item
                    current_text = self.transcript_items[event.item_id]
                    self.logger.info(f"Assistant: {current_text}")
                
                elif event.type == "response.audio_transcript.done":
                    # Transcript is complete, calculate duration and start timer
                    current_text = self.transcript_items.get(event.item_id, "")
                    self.logger.info(f"Complete transcript received: {len(current_text)} characters")
                    
                    # Calculate approximate speaking duration and wait
                    duration = self.calculate_speaking_duration(current_text)
                    
                    # Cancel any existing speaking timer
                    if self.speaking_timer:
                        self.speaking_timer.cancel()
                    
                    # Start a new timer for the speaking duration
                    self.speaking_timer = asyncio.create_task(self._wait_for_speaking_completion(duration))
    
    async def _process_audio_input(self):
            """Capture and process audio input from the microphone."""
            if not self.is_active:
                return
                
            self.logger.info("Starting audio input processing")
            
            # Initialize history for audio level tracking
            self.audio_levels = []
            self.voice_frame_counter = 0
            
            # Initialize the audio input stream
            stream = sd.InputStream(
                channels=CHANNELS,
                samplerate=SAMPLE_RATE,
                dtype="int16",
            )
            stream.start()
            
            try:
                sent_audio = False
                
                while self.is_active:
                    # Wait for the connection to be established
                    if not self.connected.is_set():
                        await asyncio.sleep(0.1)
                        continue
                        
                    # Check if there's enough audio data to read
                    if stream.read_available < READ_SIZE:
                        await asyncio.sleep(0)
                        continue
                    
                    # Check if we should be sending audio
                    if not self.should_send_audio.is_set():
                        if sent_audio:
                            self.logger.info("Audio sending paused")
                            sent_audio = False
                        await asyncio.sleep(0.1)
                        continue
                    
                    # Read audio data
                    data, _ = stream.read(READ_SIZE)
                    
                    # Get the connection
                    if not self.connection:
                        continue
                    
                    # IMPROVED AUDIO DETECTION
                    # Check if we're receiving actual speech (not just background noise)
                    audio_level = np.abs(data).mean()

                    # Add current audio level to history (keep max 10 values)
                    self.audio_levels.append(audio_level)
                    if len(self.audio_levels) > 10:
                        self.audio_levels.pop(0)

                    # Calculate average of recent audio levels
                    avg_audio_level = sum(self.audio_levels) / len(self.audio_levels)

                    # Detect speech only if audio level is significantly above background
                    # AND has been sustained for several frames
                    if audio_level > 500 and avg_audio_level > 300:  # Much higher threshold
                        # Increase counter
                        self.voice_frame_counter += 1
                        
                        # Only activate if multiple consecutive frames contain speech (about 100-200ms)
                        if self.voice_frame_counter >= 5:  # With 20ms chunks this is ~100ms of speech
                            # User is actually speaking, reset inactivity timer
                            if self.inactivity_timer and not self.model_is_responding:
                                self.logger.info("User activity detected, canceling inactivity timer")
                                self.inactivity_timer.cancel()
                                self.inactivity_timer = None
                    else:
                        # Reset counter when quiet
                        self.voice_frame_counter = 0
                    
                    # Cancel any ongoing response if we're starting to send new audio
                    if not sent_audio:
                        self.logger.info("Starting to send audio")
                        try:
                            await self.connection.send({"type": "response.cancel"})
                        except Exception as e:
                            self.logger.error("Error canceling response: %s", e)
                        sent_audio = True
                    
                    # Send the audio data
                    try:
                        await self.connection.input_audio_buffer.append(
                            audio=base64.b64encode(cast(np.ndarray, data)).decode("utf-8")
                        )
                    except Exception as e:
                        self.logger.error("Error sending audio: %s", e)
                    
                    await asyncio.sleep(0)
            
            except Exception as e:
                self.logger.error("Error in audio processing: %s", e)
            
            finally:
                # Clean up audio resources
                stream.stop()
                stream.close()
                self.logger.info("Audio input processing stopped")