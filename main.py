import asyncio

from dotenv import load_dotenv

from core.state import ConversationStateMachine
from graphs.workflow_registry import register_workflows

load_dotenv()

register_workflows()

async def main():
    state_machine = ConversationStateMachine(
        wakeword="picovoice",
    )
    
    try:
        await state_machine.run()
    except KeyboardInterrupt:
        print("Beende das Programm...")
    finally:
        state_machine.stop()


if __name__ == "__main__":
    asyncio.run(main())