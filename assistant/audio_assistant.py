from speech.voice_generator import VoiceGenerator
from util.loggin_mixin import LoggingMixin

class AudioAssistant(LoggingMixin):
    def __init__(self):
        self.voice_generator = VoiceGenerator()
    
    async def process_and_respond(self, user_text):
        """
        Verarbeitet Benutzereingabe und gibt eine Antwort zurück.
        
        Args:
            user_text (str): Die zu verarbeitende Texteingabe.
            
        Returns:
            str: Die generierte Antwort.
        """
        self.logger.info("Verarbeite Anfrage: %s", user_text)
        
        self.voice_generator.speak(user_text)
        self.logger.info("Antwort: %s", user_text)
        return user_text

    async def speak_response(self, user_text):
        """
        Generiert eine Antwort und würde sie aussprechen.
        
        Args:
            user_text (str): Die zu verarbeitende Texteingabe.
            
        Returns:
            str: Die gesprochene Antwort.
        """
        response = await self.process_and_respond(user_text)

        print(f"🤖 Assistenten-Antwort: {response}")
        return response