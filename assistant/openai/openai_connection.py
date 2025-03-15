"""OpenAI Realtime API connection management."""
import base64
import asyncio
import logging
from typing import Dict, Callable, Optional, Any

from openai import AsyncOpenAI
from openai.types.beta.realtime.session import Session
from openai.resources.beta.realtime.realtime import AsyncRealtimeConnection


class OpenAIConnection:
    """Manages connection to OpenAI's Realtime API."""
    
    def __init__(self, client: AsyncOpenAI):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client = client
        self.connection: Optional[AsyncRealtimeConnection] = None
        self.session: Optional[Session] = None
        self.event_handlers: Dict[str, Callable] = {}
    
    def register_event_callbacks(self, handlers: Dict[str, Callable]):
        self.event_handlers = handlers
    
    async def connect(self, model: str, instructions: str, voice: str):
        self.logger.info("Establishing connection to OpenAI Realtime API with model %s", model)
        
        try:
            # Hier verwenden wir async with, da client.beta.realtime.connect ein Context Manager ist
            # und keine normale async-Funktion
            self.connection_task = asyncio.create_task(self._create_and_manage_connection(model, instructions, voice))
            return True
        except Exception as e:
            self.logger.error("Error initiating connection to OpenAI: %s", e)
            raise

    async def _create_and_manage_connection(self, model, instructions, voice):
        """
        Create and manage the connection using async with.
        
        This is a separate method to handle the connection lifecycle with async with.
        """
        try:
            # Richtige Verwendung des Context Managers
            async with self.client.beta.realtime.connect(model=model) as conn:
                self.connection = conn
                self.logger.info("Connection established")
                
                # Initialize connection with session settings
                await conn.session.update(session={
                    "turn_detection": {"type": "server_vad"},
                    "voice": voice,
                    "instructions": instructions
                })
                
                # Verarbeite Events direkt hier im Context
                await self._process_events(conn)
        except Exception as e:
            self.logger.error("Error in connection management: %s", e)
        finally:
            self.logger.info("Connection context closed")
            self.connection = None
    
    async def close(self):
        """Close the connection."""
        if self.connection:
            try:
                await self.connection.close()
                self.logger.info("Connection closed")
            except Exception as e:
                self.logger.error("Error closing connection: %s", e)
            
            self.connection = None
            self.session = None
    
    async def send_audio(self, audio_data: bytes):
        """
        Send audio data to the connection.
        
        Args:
            audio_data: Raw audio data bytes
        """
        if not self.connection:
            return
            
        try:
            encoded_audio = base64.b64encode(audio_data).decode("utf-8")
            await self.connection.input_audio_buffer.append(audio=encoded_audio)
        except Exception as e:
            self.logger.error("Error sending audio: %s", e)
    
    async def cancel_response(self):
        """Cancel the current response."""
        if not self.connection:
            return
            
        try:
            await self.connection.send({"type": "response.cancel"})
            self.logger.info("Sent cancellation signal")
        except Exception as e:
            self.logger.error("Error sending cancellation: %s", e)
    
    async def _process_events(self, conn):
        """
        Process events from the connection.
        
        Args:
            conn: The realtime connection to process events from
        """
        try:
            async for event in conn:
                # Handle session events
                if event.type == "session.created":
                    self.session = event.session
                    self._dispatch_event(event.type, event)
                
                elif event.type == "session.updated":
                    self.session = event.session
                    self._dispatch_event(event.type, event)
                
                # Handle audio response
                elif event.type == "response.audio.delta":
                    # Decode audio data before dispatching
                    event.audio_bytes = base64.b64decode(event.delta)
                    self._dispatch_event(event.type, event)
                
                # Handle transcript events
                elif event.type.startswith("response.audio_transcript"):
                    self._dispatch_event(event.type, event)
        
        except Exception as e:
            self.logger.error(f"Error processing events: {e}")
    
    def _dispatch_event(self, event_type: str, event: Any):
        """
        Dispatch event to registered handler.
        
        Args:
            event_type: Type of the event
            event: Event data
        """
        handler = self.event_handlers.get(event_type)
        if handler:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Error in event handler for {event_type}: {e}")