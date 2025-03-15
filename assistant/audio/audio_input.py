"""Audio input handling from microphone."""
import asyncio
import logging
import numpy as np
from typing import Callable, Optional, List
import sounddevice as sd

SAMPLE_RATE = 24000
CHANNELS = 1
READ_SIZE = int(SAMPLE_RATE * 0.02)


class AudioInputHandler:
    """Handles audio input from the microphone with voice activity detection."""
    
    def __init__(self):
        """Initialize the audio input handler."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.running = False
        self.stream: Optional[sd.InputStream] = None
        self.processing_task: Optional[asyncio.Task] = None
        
        # Voice activity detection
        self.audio_levels: List[float] = []
        self.voice_frame_counter = 0
        
        # Callbacks
        self.on_audio_data = None
        self.on_voice_detected = None
    
    async def start(self, on_audio_data: Callable, on_voice_detected: Callable):
        """
        Start processing audio input from the microphone.
        
        Args:
            on_audio_data: Callback for when audio data is available
            on_voice_detected: Callback for when voice is detected
        """
        if self.running:
            self.logger.warning("Audio input is already running")
            return
        
        self.logger.info("Starting audio input processing")
        self.running = True
        
        # Set callbacks
        self.on_audio_data = on_audio_data
        self.on_voice_detected = on_voice_detected
        
        # Initialize audio input
        self.audio_levels = []
        self.voice_frame_counter = 0
        
        # Start the processing task
        self.processing_task = asyncio.create_task(self._process_audio())
    
    async def stop(self):
        """Stop processing audio input."""
        if not self.running:
            return
            
        self.logger.info("Stopping audio input processing")
        self.running = False
        
        # Cancel processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
            self.processing_task = None
        
        # Close the stream
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
    
    async def _process_audio(self):
        """Process audio input from the microphone."""
        try:
            # Initialize the audio input stream
            self.stream = sd.InputStream(
                channels=CHANNELS,
                samplerate=SAMPLE_RATE,
                dtype="int16",
            )
            self.stream.start()
            
            while self.running:
                # Check if there's enough audio data to read
                if self.stream.read_available < READ_SIZE:
                    await asyncio.sleep(0)
                    continue
                
                # Read audio data
                data, _ = self.stream.read(READ_SIZE)
                
                # Process the audio data
                await self._process_audio_chunk(data)
                
                await asyncio.sleep(0)
        
        except Exception as e:
            self.logger.error(f"Error in audio processing: {e}")
        
        finally:
            # Clean up audio resources
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
    
    async def _process_audio_chunk(self, data):
        """
        Process an audio chunk for voice activity and forward to callbacks.
        
        Args:
            data: Audio data chunk
        """
        # Check for voice activity
        audio_level = np.abs(data).mean()
        
        # Add current audio level to history (keep max 10 values)
        self.audio_levels.append(audio_level)
        if len(self.audio_levels) > 10:
            self.audio_levels.pop(0)
        
        # Calculate average of recent audio levels
        avg_audio_level = sum(self.audio_levels) / len(self.audio_levels)
        
        # Detect voice if audio level is significantly above background
        if audio_level > 500 and avg_audio_level > 300:  # Higher threshold
            # Increase counter
            self.voice_frame_counter += 1
            
            # Only activate if multiple consecutive frames contain voice (about 100-200ms)
            if self.voice_frame_counter >= 5:  # With 20ms chunks this is ~100ms of speech
                # Voice detected, call the callback
                if self.on_voice_detected:
                    self.on_voice_detected()
        else:
            # Reset counter when quiet
            self.voice_frame_counter = 0
        
        # Send the audio data to the callback
        if self.on_audio_data:
            await self.on_audio_data(data)