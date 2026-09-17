class ToolsRepository:
    """Registry of callable tools exposed to the model in OpenAI/Ollama function-calling format."""

    def __init__(self):
        self._tools = {}
        self._definitions = []

    def register(self, name, fn, description="", parameters=None):
        self._tools[name] = fn
        self._definitions.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters or {"type": "object", "properties": {}},
            },
        })

    def get_tool(self, name):
        return self._tools.get(name)

    def get_tool_definitions(self):
        return self._definitions
