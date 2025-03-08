import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_LLM_MODEL = "claude-3-5-haiku-latest"

TAVILY_MAX_RESULTS = 2

NOTION_API_KEY = os.getenv("NOTION_API_KEY")

DEFAULT_THREAD_ID = "1"
