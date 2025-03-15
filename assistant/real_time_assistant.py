"""
Module for interfacing with OpenAI's Realtime API for voice conversations.
With improved inactivity detection to end conversations after period of silence.
"""
import asyncio
from typing import Dict
from openai import AsyncOpenAI
from audio.audio_player_async import AudioPlayerAsync

from assistant.openai.openai_connection import OpenAIConnection
from assistant.state.conversation_timer import ConversationTimers
from assistant.audio.audio_input import AudioInputHandler

from util.loggin_mixin import LoggingMixin
from util.speaking_calculator import SpeakingCalculator

class RealtimeAssistant(LoggingMixin):
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
        super().__init__()
        
        # OpenAI components
        self.client = AsyncOpenAI()
        self.connection_handler = OpenAIConnection(self.client)
        
        # Audio components
        self.audio_player = AudioPlayerAsync()
        self.audio_input = AudioInputHandler()
        
        # Timing and state management
        self.timers = ConversationTimers(
            inactivity_timeout=inactivity_timeout,
            on_timeout=self.end_conversation
        )
        self.speaking_calculator = SpeakingCalculator()
        
        # State flags
        self.is_active = False
        self.should_send_audio = asyncio.Event()
        self.connected = asyncio.Event()
        
        # Transcript storage
        self.transcript_items: Dict[str, str] = {}
        self.last_audio_item_id = None
    
    async def start_conversation(self):
        """Start a new conversation with OpenAI Realtime API."""
        if self.is_active:
            self.logger.warning("Conversation is already active")
            return
            
        self.logger.info("Starting new conversation")
        self.is_active = True
        
        # Reset state
        self.timers.reset()
        self.connected.clear()
        self.transcript_items = {}
        
        # Start components
        self.connection_handler.register_event_callbacks({
            "session.created": self._on_session_created,
            "session.updated": self._on_session_updated,
            "response.audio.delta": self._on_audio_delta,
            "response.audio_transcript.delta": self._on_transcript_delta,
            "response.audio_transcript.done": self._on_transcript_done
        })
        
        # Start tasks
        asyncio.create_task(self._start_connection())
        asyncio.create_task(self._start_audio_input())
    
    async def _start_connection(self):
        """Start the OpenAI connection."""
        await self.connection_handler.connect(
            model="gpt-4o-mini-realtime-preview",
            instructions="Du bist ein hilfreicher Sprachassistent. Antworte primär auf Deutsch, es sei denn, der Benutzer stellt eine Frage in einer anderen Sprache. Gib kurze, präzise und informative Antworten. Sprich natürlich und freundlich, als ob du mit einem Menschen sprichst.",
            voice="shimmer"
        )
        
        self.connected.set()
        self.should_send_audio.set()
    
    async def _start_audio_input(self):
        """Start processing audio input."""
        await self.audio_input.start(
            on_audio_data=self._on_audio_data,
            on_voice_detected=self._on_voice_detected
        )
    
    async def end_conversation(self):
        """End the current conversation."""
        if not self.is_active:
            return
            
        self.logger.info("Ending conversation")
        
        # Stop components
        self.should_send_audio.clear()
        self.timers.cancel_all()
        await self.connection_handler.close()
        await self.audio_input.stop()
        
        # Reset state
        self.is_active = False
        self.connected.clear()
        self.transcript_items = {}
    
    async def cancel_current_interaction(self):
        """Cancel the current interaction but keep the connection open."""
        if not self.is_active:
            return
            
        self.logger.info("Canceling current interaction")
        self.should_send_audio.clear()
        await self.connection_handler.cancel_response()
    
    # Event handlers
    def _on_session_created(self, event):
        """Handle session created event."""
        self.logger.info("Session created: %s", event.session.id)
    
    def _on_session_updated(self, event):
        """Handle session updated event."""
        pass
    
    def _on_audio_delta(self, event):
        """Handle audio delta event."""
        # Update the last audio time
        self.timers.update_model_speaking()
        
        # Handle audio response from the assistant
        if event.item_id != self.last_audio_item_id:
            self.audio_player.reset_frame_count()
            self.last_audio_item_id = event.item_id
            
        self.audio_player.add_data(event.audio_bytes)
    
    def _on_transcript_delta(self, event):
        """Handle transcript delta event."""
        # Handle text transcript of the assistant's audio response
        if event.item_id in self.transcript_items:
            self.transcript_items[event.item_id] += event.delta
        else:
            self.transcript_items[event.item_id] = event.delta
            
        # Print the full current transcript for this item
        current_text = self.transcript_items[event.item_id]
        self.logger.info("Assistant: %s", current_text)
    
    def _on_transcript_done(self, event):
        """Handle transcript done event."""
        # Transcript is complete, calculate duration and start timer
        current_text = self.transcript_items.get(event.item_id, "")
        self.logger.info("Complete transcript received: %d characters", len(current_text))
        
        # Calculate approximate speaking duration
        duration = self.speaking_calculator.calculate_duration(current_text)
        
        # Start a timer for when the model should be done speaking
        self.timers.start_speaking_timer(duration)
    
    async def _on_audio_data(self, audio_data):
        """Handle audio data from the microphone."""
        if self.connected.is_set() and self.should_send_audio.is_set():
            await self.connection_handler.send_audio(audio_data)
    
    def _on_voice_detected(self):
        """Handle voice detection event."""
        # Cancel inactivity timer when user speaks
        self.timers.cancel_inactivity_timer()