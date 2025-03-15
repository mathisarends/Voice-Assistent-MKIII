#!/usr/bin/env python3
"""
Main module for the voice assistant using OpenAI Realtime API with wake word activation.
"""
import time
import asyncio
import logging
import queue
import threading

# Import custom modules
from real_time_assistant import RealtimeAssistant
from audio.audio_manager import play
from speech.wake_word_listener import WakeWordListener

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("voice_assistant")

# Command queue for communication between threads
command_queue = queue.Queue()

class VoiceAssistant:
    """Main voice assistant class that coordinates wake word detection and OpenAI API interaction"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("🚀 Initializing Voice Assistant with OpenAI Realtime API")
        
        # Create the assistant that will handle real-time communication
        self.realtime_assistant = RealtimeAssistant()
        
        # State management
        self.running = False
        self.in_conversation = False
        
        # Define wake words and listeners
        self.main_wake_listener = None
        self.command_wake_listener = None
        
    async def start(self):
        """Start the voice assistant"""
        self.logger.info("Starting voice assistant service")
        self.running = True
        
        # Initialize main wake word listener with our chosen wake word
        self.main_wake_listener = WakeWordListener(wakeword="computer", sensitivity=0.85)
        
        # Start wake word detection thread
        threading.Thread(
            target=self._wake_word_detection_thread,
            daemon=True
        ).start()
        
        # Start the main asyncio loop
        await self._main_loop()
    
    def _wake_word_detection_thread(self):
        """Thread that listens for the main wake word"""
        self.logger.info("🎤 Starting main wake word detection thread")
        
        try:
            while self.running:
                if not self.in_conversation:
                    # Wait for wake word when not in conversation
                    if self.main_wake_listener.listen_for_wakeword():
                        # Put a command in the queue for the main loop to process
                        command_queue.put("start_conversation")
                else:
                    # When in conversation, just sleep briefly
                    time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error in main wake word detection thread: {e}")
        finally:
            self.logger.info("Main wake word detection thread ended")
    
    def _command_word_detection_thread(self):
        """Thread that listens for command words during a conversation"""
        self.logger.info("🎤 Starting command word detection thread")
        
        try:
            # Create a wake word listener for command words
            self.command_wake_listener = WakeWordListener(wakeword="thanks", sensitivity=0.7)
            
            while self.running and self.in_conversation:
                # Listen for command words
                if self.command_wake_listener.listen_for_wakeword():
                    # Put a command in the queue for the main loop to process
                    command_queue.put("end_conversation")
                
                # Small delay to check if we should exit
                time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Error in command word detection thread: {e}")
        finally:
            self.logger.info("Command word detection thread ended")
            # Clean up the command listener
            if self.command_wake_listener:
                self.command_wake_listener.cleanup()
                self.command_wake_listener = None
    
    async def _main_loop(self):
        """Main asyncio loop that processes commands from the queue"""
        self.logger.info("Starting main asyncio loop")
        
        try:
            while self.running:
                try:
                    # Check for commands from the wake word threads (non-blocking)
                    while not command_queue.empty():
                        command = command_queue.get_nowait()
                        
                        if command == "start_conversation":
                            self.logger.info("🔔 Wake word detected, starting conversation")
                            self.in_conversation = True
                            
                            # Start command word detection in a separate thread
                            threading.Thread(
                                target=self._command_word_detection_thread,
                                daemon=True
                            ).start()
                            
                            # Start conversation with OpenAI (non-blocking)
                            asyncio.create_task(self._handle_conversation())
                            
                        elif command == "end_conversation":
                            self.logger.info("Command word detected, ending conversation")
                            self.in_conversation = False
                            
                            # End conversation (non-blocking)
                            if self.realtime_assistant.is_active:
                                asyncio.create_task(self.realtime_assistant.end_conversation())
                                play("stop-listening")
                    
                    # Small sleep to prevent CPU overuse
                    await asyncio.sleep(0.1)
                except queue.Empty:
                    # No commands, just continue
                    pass
        except KeyboardInterrupt:
            self.logger.info("🛑 Program manually terminated")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error in main loop: {e}")
        finally:
            # Cleanup on exit
            await self.stop()
    
    async def _handle_conversation(self):
        """Handle a conversation with the OpenAI assistant"""
        try:
            # Start conversation with OpenAI
            await self.realtime_assistant.start_conversation()
            
            # Keep the task alive until conversation is done
            while self.realtime_assistant.is_active and self.in_conversation:
                await asyncio.sleep(0.1)
            
            # Make sure conversation is ended
            if self.realtime_assistant.is_active:
                await self.realtime_assistant.end_conversation()
            
            self.in_conversation = False
            
        except Exception as e:
            self.logger.error(f"Error in conversation: {e}")
            self.in_conversation = False
    
    async def stop(self):
        """Stop the voice assistant and clean up resources"""
        self.logger.info("Stopping voice assistant")
        self.running = False
        self.in_conversation = False
        
        # Clean up wake word listeners
        if self.main_wake_listener:
            self.main_wake_listener.cleanup()
        
        if self.command_wake_listener:
            self.command_wake_listener.cleanup()
        
        # Clean up any active conversations
        if self.realtime_assistant.is_active:
            await self.realtime_assistant.end_conversation()

async def main():
    """Main entry point for the voice assistant application"""
    
    assistant = VoiceAssistant()
    await assistant.start()

if __name__ == "__main__":
    asyncio.run(main())