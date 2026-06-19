"""Groq API client settings (OpenAI-compatible)."""

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"

# Higher quality, lower daily volume (100k TPD on free tier):
# DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
