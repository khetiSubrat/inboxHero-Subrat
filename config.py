import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration for inboxHero models and services."""
    
    # Gemini Configuration
    gemini_api_key = os.getenv("GEMINI_API_KEY", None)
    has_gemini_key = gemini_api_key is not None
    
    # Ollama Configuration
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    # Model Provider Selection
    # Must be set via MODEL_PROVIDER env var: 'gemini' or 'ollama'
    model_provider = os.getenv("MODEL_PROVIDER", "").lower()

# Create singleton instance
config = Config()
