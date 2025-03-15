"""
Module for interfacing with OpenAI's Realtime API for voice conversations.
"""
import base64
import asyncio
import logging
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
    
    def __init__(self):
        """Initialize the realtime assistant."""
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
        
        # Collected text responses
        self.transcript_items: Dict[str, str] = {}
    
    async def start_conversation(self):
        """Start a new conversation with OpenAI Realtime API."""
        if self.is_active:
            self.logger.warning("Conversation is already active")
            return
            
        self.logger.info("Starting new conversation")
        self.is_active = True
        
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
        
        # Close the connection if it exists
        if self.connection:
            try:
                await self.connection.close()
            except Exception as e:
                self.logger.error(f"Error closing connection: {e}")
            
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
            self.logger.error(f"Error sending cancellation: {e}")
    
    async def _handle_realtime_connection(self):
        """Establish and handle the connection with OpenAI Realtime API."""
        if not self.is_active:
            return
        
        self.logger.info("Establishing connection to OpenAI Realtime API")
        
        async with self.client.beta.realtime.connect(model="gpt-4o-realtime-preview") as conn:
            self.connection = conn
            self.connected.set()
            
            # Configure the session with server-side voice activity detection
            await conn.session.update(session={"turn_detection": {"type": "server_vad"}})
            
            # Start sending audio immediately
            self.should_send_audio.set()
            
            # Process events from the connection
            async for event in conn:
                if not self.is_active:
                    break
                    
                if event.type == "session.created":
                    self.session = event.session
                    self.logger.info(f"Session created: {event.session.id}")
                    
                elif event.type == "session.updated":
                    self.session = event.session
                    
                elif event.type == "response.audio.delta":
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
    
    async def _process_audio_input(self):
        """Capture and process audio input from the microphone."""
        if not self.is_active:
            return
            
        self.logger.info("Starting audio input processing")
        
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
                
                # Cancel any ongoing response if we're starting to send new audio
                if not sent_audio:
                    self.logger.info("Starting to send audio")
                    try:
                        await self.connection.send({"type": "response.cancel"})
                    except Exception as e:
                        self.logger.error(f"Error canceling response: {e}")
                    sent_audio = True
                
                # Send the audio data
                try:
                    await self.connection.input_audio_buffer.append(
                        audio=base64.b64encode(cast(np.ndarray, data)).decode("utf-8")
                    )
                except Exception as e:
                    self.logger.error(f"Error sending audio: {e}")
                
                await asyncio.sleep(0)
        
        except Exception as e:
            self.logger.error(f"Error in audio processing: {e}")
        
        finally:
            # Clean up audio resources
            stream.stop()
            stream.close()
            self.logger.info("Audio input processing stopped")