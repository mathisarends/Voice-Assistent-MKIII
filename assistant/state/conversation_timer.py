import asyncio
import time
from typing import Callable, Optional
import logging

class ConversationTimers:
    """Manages timing aspects of the conversation like inactivity detection."""
    
    def __init__(self, inactivity_timeout: int = 15, on_timeout: Callable = None):
        """
        Initialize timer manager.
        
        Args:
            inactivity_timeout: Seconds of silence before ending conversation
            on_timeout: Callback function to execute when timeout occurs
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.inactivity_timeout = inactivity_timeout
        self.on_timeout = on_timeout
        
        # Timer tasks
        self.inactivity_timer: Optional[asyncio.Task] = None
        self.speaking_timer: Optional[asyncio.Task] = None
        self.response_monitor_task: Optional[asyncio.Task] = None
        
        # State tracking
        self.model_is_responding = False
        self.last_model_audio_time = 0
    
    def reset(self):
        """Reset all timers and state."""
        self.cancel_all()
        self.model_is_responding = False
        self.last_model_audio_time = 0
        
        # Start monitoring for model responses
        self.response_monitor_task = asyncio.create_task(self._monitor_model_responses())
    
    def cancel_all(self):
        """Cancel all active timers."""
        for timer_attr in ['inactivity_timer', 'speaking_timer', 'response_monitor_task']:
            timer = getattr(self, timer_attr)
            if timer:
                timer.cancel()
                setattr(self, timer_attr, None)
    
    def cancel_inactivity_timer(self):
        """Cancel the inactivity timer if it's running."""
        if self.inactivity_timer:
            self.logger.info("Canceling inactivity timer due to user activity")
            self.inactivity_timer.cancel()
            self.inactivity_timer = None
    
    def update_model_speaking(self):
        """Update the state to indicate the model is currently speaking."""
        self.last_model_audio_time = time.time()
        
        if not self.model_is_responding:
            self.model_is_responding = True
            self.logger.info("Model started responding")
            
            # Cancel inactivity timer while model is speaking
            self.cancel_inactivity_timer()
    
    def start_speaking_timer(self, duration: float):
        """
        Start a timer for the calculated speaking duration.
        
        Args:
            duration: Estimated speaking duration in seconds
        """
        # Cancel any existing speaking timer
        if self.speaking_timer:
            self.speaking_timer.cancel()
        
        # Start a new timer
        self.speaking_timer = asyncio.create_task(self._wait_for_speaking_completion(duration))
    
    async def start_inactivity_timer(self):
        """Start a timer that will end the conversation after inactivity."""
        # Cancel any existing timer
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
        
        # Create a new timer
        self.inactivity_timer = asyncio.create_task(self._inactivity_timeout_handler())
    
    async def _wait_for_speaking_completion(self, duration: float):
        """
        Wait for the model to finish speaking and then start the inactivity timer.
        
        Args:
            duration: Estimated speaking duration in seconds
        """
        self.logger.info("Waiting %.2f seconds for model to finish speaking", duration)
        try:
            # Wait for the calculated speaking duration
            await asyncio.sleep(duration)
            
            # Model has finished speaking, start the inactivity timer
            self.logger.info("Speaking timer completed, starting inactivity timer")
            self.model_is_responding = False
            await self.start_inactivity_timer()
        except asyncio.CancelledError:
            # Timer was cancelled
            pass
    
    async def _inactivity_timeout_handler(self):
        """Handle inactivity timeout - end the conversation after specified time."""
        self.logger.info("Starting inactivity timer (%d seconds)", self.inactivity_timeout)
        try:
            # Wait for the timeout period
            await asyncio.sleep(self.inactivity_timeout)
            
            # If we get here, the timer wasn't cancelled, which means there was no activity
            self.logger.info("No user activity for %d seconds after model response", self.inactivity_timeout)
            
            # Call the timeout callback if provided
            if self.on_timeout:
                await self.on_timeout()
        except asyncio.CancelledError:
            # Timer was cancelled because of user activity
            self.logger.info("Inactivity timer cancelled")
    
    async def _monitor_model_responses(self):
        """Monitor when the model is responding and detect when it stops."""
        try:
            while True:  # Run until cancelled
                if self.model_is_responding and not self.speaking_timer:
                    # Check if model has stopped responding
                    current_time = time.time()
                    time_since_last_audio = current_time - self.last_model_audio_time
                    
                    if time_since_last_audio > 1.0:  # 1 second without audio means model likely stopped
                        self.logger.info("Detected end of model response (no audio for 1 second)")
                        self.model_is_responding = False
                        
                        # Start the inactivity timer
                        await self.start_inactivity_timer()
                
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error("Error in model response monitor: %s", e)