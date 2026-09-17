import urllib.request
import urllib.error
import json 
from base_model import BaseModel
from config import config

class OllamaModel(BaseModel):
    def __init__(self, host: str = ""):
        # Initialize Ollama-specific things here
        super().__init__()
        self.host = host or config.ollama_host
        print("Ollama model initialized")
        if self.verify_server_is_running():
            print("Ollama server verification succeeded.")
            model_list = self.get_installed_models()
            if model_list:
                print("Installed models:", model_list)
                self.choose_model = model_list[0]  # Choose the first model by default
        else :
            print("Ollama server verification failed.")

    def verify_server_is_running(self):
        """Ping Ollama API to verify the service is running."""
        try:
            # We ping /api/tags which returns 200 OK when Ollama is running
            url = f"{self.host.rstrip('/')}/api/tags"
            req = urllib.request.Request(url, method="GET")
            
            with urllib.request.urlopen(req, timeout=2):
                #pass  # Server is up and reachable
                print(f"Ollama server is running at {self.host}.")
                return True
        except (urllib.error.URLError, TimeoutError, ConnectionRefusedError) as e:
            raise RuntimeError(
                f"Ollama server is not running at {self.host}. "
                "Please start it with `ollama serve` before creating this model."
            ) from e

    def get_installed_models(self) -> list[str]:
        """Returns a list of installed model names."""
        try:
            url = f"{self.host.rstrip('/')}/api/tags"
            req = urllib.request.Request(url, method="GET")
            
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))
                # Extract just the model names
                return [model["name"] for model in data.get("models", [])]
                
        except Exception as e:
            print(f"Could not retrieve models: {e}")
            return []

    def _chat(self, messages, tools=None):
        """Call Ollama chat API with optional tool definitions."""
        url = f"{self.host.rstrip('/')}/api/chat"
        payload = {
            "model": self.choose_model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama API error {e.code}: {error_body}") from e
        except (urllib.error.URLError, TimeoutError, ConnectionRefusedError) as e:
            raise RuntimeError(
                f"Could not reach Ollama server at {self.host}. Ensure `ollama serve` is running."
            ) from e