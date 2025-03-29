import asyncio
import traceback
from abc import ABC, abstractmethod
from typing import Optional

from typing_extensions import override

from assistant.speech_service import SpeechService
from audio.strategy.audio_manager import get_audio_manager
from graphs.workflow_dispatcher import WorkflowDispatcher
from speech.recognition.audio_transcriber import AudioTranscriber
from speech.recognition.whisper_speech_recognition import \
    WhisperSpeechRecognition
from speech.wake_word_listener import WakeWordListener
from tools.lights.animation.light_animation import (AnimationType,
                                                    LightAnimationFactory)
from tools.lights.bridge.bridge import HueBridge
from tools.lights.light_controller import LightController
from util.loggin_mixin import LoggingMixin


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
    
    def __init__(self, wakeword_listener: WakeWordListener, speech_service: SpeechService, speech_recorder: WhisperSpeechRecognition):
        super().__init__()
        self.wakeword_listener = wakeword_listener
        self.speech_service = speech_service
        self.speech_recorder = speech_recorder
    
    async def process(self) -> Optional['ConversationState']:
        self.logger.info("🎤 Warte auf Wake-Word...")
        
        if self.wakeword_listener.listen_for_wakeword():
            self.play_audio_feedback("wakesound")
            self.logger.info("🔔 Wake-Word erkannt!")
            
            return WakeWordDetectedState(
                speech_service=self.speech_service,
                speech_recorder=self.speech_recorder
            )
        
        await asyncio.sleep(0.1)
        return None
    

class WakeWordDetectedState(ConversationState):
    """Zustand nach Wake-Word-Erkennung, startet Audioaufnahme"""
    
    def __init__(self, speech_service: SpeechService, speech_recorder: WhisperSpeechRecognition):
        super().__init__()
        self.speech_service = speech_service
        self.speech_recorder = speech_recorder
    
    @override
    async def process(self):
        self.logger.info("🎙️ Starte Sprachaufnahme...")
        self.speech_service.interrupt_and_reset()
        await self.provide_light_feedback()
        
        try:
            audio_data = self.speech_recorder.record_audio()
            
            audio_transcriber = AudioTranscriber()
            
            return TranscribingState(
                audio_transcriber=audio_transcriber,
                audio_data=audio_data,
            )
            
        except Exception as e:
            return self.handle_error(e)
        


class TranscribingState(ConversationState):
    """Transkribiert die aufgenommene Sprache"""
    
    def __init__(self, audio_transcriber: AudioTranscriber, audio_data):
        super().__init__()
        self.audio_transcriber = audio_transcriber
        self.audio_data = audio_data
        
    @override
    async def process(self):
        self.logger.info("📝 Transkribiere Audiodaten...")
        await self.provide_light_feedback()
        
        try:
            user_prompt = await self.audio_transcriber.transcribe_audio(
                self.audio_data
            )
            
            if not user_prompt or user_prompt.strip() == "":
                return self.handle_error("Keine Sprache erkannt oder leerer Text")
            
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
    
    def __init__(sel):
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