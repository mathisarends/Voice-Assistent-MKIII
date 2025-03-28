import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_LLM_MODEL = "claude-3-5-haiku-latest"
GPT_MINI = "gpt-4o-mini"
GPT = "gpt-4o"

GEMINI_FLASH = "gemini-2.0-flash"

TAVILY_MAX_RESULTS = 2

NOTION_API_KEY = os.getenv("NOTION_API_KEY")

DEFAULT_THREAD_ID = "1"
