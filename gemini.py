from google import genai
from google.genai import types

from base_model import BaseModel
from config import config


class GeminiModel(BaseModel):
    def __init__(self, model_name: str = "gemini-flash-lite-latest"):
        super().__init__(model_name=model_name)
        if not config.has_gemini_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file before using GeminiModel."
            )
        self.client = genai.Client(api_key=config.gemini_api_key)
        print("Gemini model initialized")

    def _to_gemini_tools(self, tools):
        if not tools:
            return None
        declarations = [
            types.FunctionDeclaration(**tool["function"]) for tool in tools
        ]
        return [types.Tool(function_declarations=declarations)]

    def _to_gemini_content(self, message):
        """Convert one internal message dict into a Gemini Content turn."""
        role = message.get("role")

        if role == "tool":
            return types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(
                        name=message.get("name", "unknown_tool"),
                        response={"result": message.get("content", "")},
                    )
                ],
            )

        if role == "assistant":
            parts = []
            for tool_call in message.get("tool_calls", []) or []:
                function_data = tool_call.get("function", {})
                parts.append(
                    types.Part(
                        function_call=types.FunctionCall(
                            name=function_data.get("name"),
                            args=function_data.get("arguments", {}),
                        ),
                        thought_signature=tool_call.get("thought_signature"),
                    )
                )
            if message.get("content"):
                parts.append(types.Part(text=message["content"]))
            return types.Content(role="model", parts=parts)

        return types.Content(role="user", parts=[types.Part(text=message.get("content", ""))])

    def _chat(self, messages, tools=None):
        contents = [self._to_gemini_content(message) for message in messages]

        response = self.client.models.generate_content(
            model=self.choose_model,
            contents=contents,
            config=types.GenerateContentConfig(tools=self._to_gemini_tools(tools)),
        )

        candidate = response.candidates[0] if response.candidates else None
        parts = candidate.content.parts if candidate and candidate.content else []

        tool_calls = []
        text_parts = []
        for part in parts:
            if getattr(part, "function_call", None):
                tool_calls.append(
                    {
                        "function": {
                            "name": part.function_call.name,
                            "arguments": dict(part.function_call.args or {}),
                        },
                        "thought_signature": getattr(part, "thought_signature", None),
                    }
                )
            elif getattr(part, "text", None):
                text_parts.append(part.text)

        return {
            "message": {
                "role": "assistant",
                "content": "".join(text_parts),
                "tool_calls": tool_calls,
            }
        }