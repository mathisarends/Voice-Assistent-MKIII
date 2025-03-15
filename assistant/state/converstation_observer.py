"""
Observer Pattern für RealtimeAssistant zur Benachrichtigung über Konversationsstatus-Änderungen.
"""
from typing import List
import logging

# 1. Definiere ein Event-System

class ConversationEvent:
    """Basisklasse für Konversationsereignisse."""
    pass

class ConversationStartedEvent(ConversationEvent):
    """Ereignis, das ausgelöst wird, wenn eine Konversation startet."""
    pass

class ConversationEndedEvent(ConversationEvent):
    def __init__(self, reason: str = "unknown"):
        self.reason = reason  # z.B. "timeout", "user_request", "api_error"

class ConversationErrorEvent(ConversationEvent):
    def __init__(self, error: Exception):
        self.error = error

# 2. Observer-Interface

class ConversationObserver:
    """Interface für Klassen, die Konversationsereignisse beobachten wollen."""
    
    def on_conversation_started(self, event: ConversationStartedEvent):
        """Wird aufgerufen, wenn eine Konversation startet."""
        pass
    
    def on_conversation_ended(self, event: ConversationEndedEvent):
        """Wird aufgerufen, wenn eine Konversation endet."""
        pass
    
    def on_conversation_error(self, event: ConversationErrorEvent):
        """Wird aufgerufen, wenn ein Fehler in der Konversation auftritt."""
        pass

# 3. Observable-Mixin für RealtimeAssistant

class ConversationObservable:
    """Mixin für Klassen, die Konversationsereignisse veröffentlichen."""
    
    def __init__(self):
        self._observers: List[ConversationObserver] = []
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def add_observer(self, observer: ConversationObserver):
        """Fügt einen Beobachter hinzu."""
        if observer not in self._observers:
            self._observers.append(observer)
            self._logger.debug("Observer added: %s", observer.__class__.__name__)
    
    def remove_observer(self, observer: ConversationObserver):
        """Entfernt einen Beobachter."""
        if observer in self._observers:
            self._observers.remove(observer)
            self._logger.debug("Observer removed: %s", observer.__class__.__name__)
    
    def notify_conversation_started(self):
        """Benachrichtigt alle Beobachter, dass eine Konversation gestartet wurde."""
        event = ConversationStartedEvent()
        self._logger.debug("Notifying conversation started")
        for observer in self._observers:
            try:
                observer.on_conversation_started(event)
            except Exception as e:
                self._logger.error("Error notifying observer %s: %s", observer.__class__.__name__, e)
    
    def notify_conversation_ended(self, reason: str = "unknown"):
        """Benachrichtigt alle Beobachter, dass eine Konversation beendet wurde."""
        event = ConversationEndedEvent(reason)
        self._logger.debug("Notifying conversation ended (reason: %s)", reason)
        for observer in self._observers:
            try:
                observer.on_conversation_ended(event)
            except Exception as e:
                self._logger.error("Error notifying observer %s: %s", observer.__class__.__name__, e)
    
    def notify_conversation_error(self, error: Exception):
        """Benachrichtigt alle Beobachter über einen Fehler in der Konversation."""
        event = ConversationErrorEvent(error)
        self._logger.debug("Notifying conversation error: %s", error)
        for observer in self._observers:
            try:
                observer.on_conversation_error(event)
            except Exception as e:
                self._logger.error("Error notifying observer %s: %s", observer.__class__.__name__, e)