import asyncio

from dotenv import load_dotenv

from core.state import ConversationStateMachine
from graphs.workflow_registry import register_workflows
from service.service_locator import ServiceLocator

load_dotenv()

register_workflows()

service_lcoator = ServiceLocator.get_instance()

async def main():
    state_machine = ConversationStateMachine(
        wakeword="picovoice",
    )
    
    try:
        await state_machine.run()
    except KeyboardInterrupt:
        print("Beende das Programm...")
    finally:
        service_lcoator.get_speech_service().shutdown()
        service_lcoator.get_wake_word_listener().cleanup()
        state_machine.stop()


if __name__ == "__main__":
    asyncio.run(main())