from config import config
from ollama import OllamaModel
from gemini import GeminiModel


class FactoryModel:
    def __init__(self):
        pass

    def create_model(self):
        """
        Select a model provider based on the required MODEL_PROVIDER env var.
        """
        if config.model_provider == "ollama":
            return OllamaModel(host="")
        if config.model_provider == "gemini":
            return GeminiModel()

        raise ValueError(
            "MODEL_PROVIDER is not set. Set MODEL_PROVIDER=gemini or MODEL_PROVIDER=ollama in .env."
        )