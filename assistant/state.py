import asyncio
import time
import traceback
from abc import ABC, abstractmethod
from typing import Optional

from typing_extensions import override

from assistant.service_locator import ServiceLocator
from audio.strategy.audio_manager import get_audio_manager
from graphs.workflow_dispatcher import WorkflowDispatcher
from speech.wake_word_listener import WakeWordListener
from tools.lights.animation.light_animation import (AnimationType,
                                                    LightAnimationFactory)
from tools.lights.bridge import HueBridge
from tools.lights.light_controller import LightController
from util.decorator import non_blocking
from util.loggin_mixin import LoggingMixin


class ConversationStateMachine(LoggingMixin):
    _instance = None
    wakeword_listener = None

    def __init__(
        self,
        wakeword="picovoice",
        
    ):
        super().__init__()
        self.wakeword = wakeword
        self.audio_manager = get_audio_manager()
        self.should_stop = False
        self.current_state = None
        
        ConversationStateMachine._instance = self

    @classmethod
    def get_instance(cls):
        return cls._instance

    async def run(self):
        """Startet die Zustandsmaschine"""
        async with WakeWordListener.create(wakeword=self.wakeword) as wakeword_listener:
            ConversationStateMachine.wakeword_listener = wakeword_listener
            
            # Setze den initialen Zustand
            self.current_state = WaitingForWakeWordState()
            
            await self._run_state_machine()

    async def _run_state_machine(self):
        while not self.should_stop:
            try:
                # Verarbeite den aktuellen Zustand
                next_state = await self.current_state.process()
                
                if next_state is None:
                    self.current_state = WaitingForWakeWordState()
                else:
                    self.current_state = next_state
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Programm manuell beendet.")
                self.should_stop = True
                
            except Exception as e:
                self.logger.error("❌ Unerwarteter Fehler in der Zustandsmaschine: %s", e)
                self.logger.error("Traceback: %s", traceback.format_exc())
                
                self.current_state = WaitingForWakeWordState()

    def stop(self):
        self.should_stop = True
        self.logger.info("Zustandsmaschine wird gestoppt...")


class ConversationState(ABC, LoggingMixin):
    def __init__(self):
        super().__init__()
        
        self.audio_manager = get_audio_manager()
        
        bridge = HueBridge.connect_by_ip()
        controller = LightController(bridge)
        self.light_animation_factory = LightAnimationFactory(controller)
        
        self._next_state = None

    @abstractmethod
    async def process(self) -> Optional['ConversationState']:
        """
        Führt die Logik des Zustands aus und gibt entweder den nächsten Zustand
        zurück oder None, wenn im aktuellen Zustand bleiben soll.
        """
        pass
    
    def play_audio_feedback(self, sound_name):
        self.audio_manager.play(sound_name)
    
    @non_blocking
    async def provide_light_feedback(self):
        print(f"🔦 Lichtszene für {self.get_name()} wird aktiviert")

    def get_name(self):
        return self.__class__.__name__
    
    def handle_error(self, exception) -> 'ErrorState':
        error_message = str(exception)
        source_state = self.get_name()
        
        if isinstance(exception, Exception):
            self.logger.error(f"❌ Fehler in {source_state}: {error_message}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        else:
            self.logger.error(f"❌ Fehlerfall in {source_state}: {error_message}")
        
        return ErrorState()
    

class WaitingForWakeWordState(ConversationState):
    """Wartet auf die Erkennung des Wake-Words"""
    
    def __init__(self):
        super().__init__()
        # No need to pass wakeword_listener as a parameter

    async def process(self) -> Optional['ConversationState']:
        self.logger.info("🎤 Warte auf Wake-Word...")
        
        # Access the wakeword_listener from the ConversationStateMachine
        wakeword_listener = ConversationStateMachine.wakeword_listener
        
        if wakeword_listener.listen_for_wakeword():
            self.play_audio_feedback("wakesound")
            self.logger.info("🔔 Wake-Word erkannt!")
            
            await self.provide_light_feedback()
            
            time.sleep(1) # TODO: Die audio sollte eigentlich blockierend abgespielt werden.
            
            return WakeWordDetectedState()
        
        await asyncio.sleep(0.1)
        return None
    
    @override
    @non_blocking
    async def provide_light_feedback(self):
        wake_flash_anim = self.light_animation_factory.get_animation(animation_type=AnimationType.WAKE_FLASH)
        await wake_flash_anim.execute(["1", "5", "6", "7"])


class WakeWordDetectedState(ConversationState):
    """Zustand nach Wake-Word-Erkennung, startet Audioaufnahme"""
    
    def __init__(self):
        super().__init__()
        self.speech_service = ServiceLocator().get_instance().get_speech_service()
        self.speech_recorder = ServiceLocator().get_instance().get_speech_recorder()
    
    @override
    async def process(self):
        self.logger.info("🎙️ Starte Sprachaufnahme...")
        self.speech_service.interrupt_and_reset()
        
        try:
            audio_data = self.speech_recorder.record_audio()
            
            return TranscribingState(
                audio_data=audio_data,
            )
            
        except Exception as e:
            return self.handle_error(e)
        

class TranscribingState(ConversationState):
    """Transkribiert die aufgenommene Sprache"""
    
    def __init__(self, audio_data):
        super().__init__()
        self.audio_data = audio_data
        self.audio_transcriber = ServiceLocator.get_instance().get_audio_transcriber()
        
    @override
    async def process(self):
        self.logger.info("📝 Transkribiere Audiodaten...")
        
        try:
            user_prompt = await self.audio_transcriber.transcribe_audio(
                self.audio_data
            )
            
            if not user_prompt or user_prompt.strip() == "":
                 self.play_audio_feedback("stop-listening-no-message")
                 return WaitingForWakeWordState()
            
            self.logger.info("🗣 Erkannt: %s", user_prompt)
            
            workflow_dispatcher = WorkflowDispatcher()
            
            return DispatchingState(
                workflow_dispatcher=workflow_dispatcher,
                user_prompt=user_prompt
            )
            
        except Exception as e:
            return self.handle_error(e)


class DispatchingState(ConversationState):
    """Leitet die Anfrage an den entsprechenden Workflow weiter"""
    
    def __init__(self, workflow_dispatcher: WorkflowDispatcher, user_prompt: str):
        super().__init__()
        self.workflow_dispatcher = workflow_dispatcher
        self.user_prompt = user_prompt
        
    @override
    async def process(self):
        self.logger.info("🔄 Verarbeite Anfrage und wähle Workflow...")
        await self.provide_light_feedback()
        
        try:
            print("use prompt:", self.user_prompt)
            result = await self.workflow_dispatcher.dispatch(self.user_prompt)
            self.logger.info("🤖 AI-Antwort: %s", result)
            
            return None
            
        except Exception as e:
            return self.handle_error(e)
        

class ErrorState(ConversationState):
    """
    Zustand für Fehlerbehandlung - wird aktiviert, wenn in einem anderen Zustand
    ein Fehler auftritt. Bietet Feedback und beendet dann die Zustandskette.
    """
    
    def __init__(self):
        super().__init__()
    
    @override
    async def process(self):
        self.play_audio_feedback("error-1")
        await self.provide_light_feedback()
                
        return None
    
    @override
    async def provide_light_feedback(self):
        error_anim = self.light_animation_factory.get_animation(AnimationType.ERROR_FLASH)
        await error_anim.execute(["5", "6", "7"], transition_time=2, hold_time=0.5)