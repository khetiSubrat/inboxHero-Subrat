from abc import ABC, abstractmethod
from typing import Any, Optional

from planner import Planner
from reflector import Reflector
from tools import ToolsRepository


class BaseModel(ABC):
    def __init__(self, model_name: Optional[str] = None):
        self.choose_model = model_name
        self.tool_repository = ToolsRepository()
        tool_names = [tool["function"]["name"] for tool in self.tool_repository.get_tool_definitions()]
        self.planner = Planner(self, tool_names=tool_names)
        self.reflector = Reflector(self)

    @abstractmethod
    def _chat(self, messages: list[dict[str, Any]], tools=None) -> dict[str, Any]:
        """Provider-specific chat API call."""

    def _extract_assistant_message(self, data: dict[str, Any]) -> dict[str, Any]:
        return data.get("message", {})

    def _extract_tool_calls(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        return message.get("tool_calls", []) or []

    def _extract_content(self, message: dict[str, Any]) -> str:
        return message.get("content", "")

    def _execute_tool_call(self, tool_call: dict[str, Any]) -> tuple[str, Any]:
        function_data = tool_call.get("function", {})
        tool_name = function_data.get("name", "unknown_tool")
        tool_args = function_data.get("arguments", {})

        tool_fn = self.tool_repository.get_tool(tool_name)
        if not tool_fn:
            return tool_name, {"status": "error", "message": f"Tool '{tool_name}' is not registered."}

        if not isinstance(tool_args, dict):
            return tool_name, {"status": "error", "message": f"Invalid arguments for tool '{tool_name}'."}

        try:
            return tool_name, tool_fn(**tool_args)
        except TypeError as e:
            # Missing/unexpected arguments supplied by the model for this tool.
            return tool_name, {"status": "error", "message": f"Bad arguments for tool '{tool_name}': {e}"}
        except Exception as e:
            return tool_name, {"status": "error", "message": f"Tool '{tool_name}' failed: {e}"}

    def _build_tool_result_message(self, tool_name: str, tool_result: Any) -> dict[str, Any]:
        return {
            "role": "tool",
            "name": tool_name,
            "content": str(tool_result),
        }

    def _trace(self, label: str, detail: str = "") -> None:
        """Print one step of the Goal->Plan->Tool->Observation->Answer->Reflection run trace."""
        print(f"[TRACE] {label}{': ' + detail if detail else ''}")

    def generate(self, prompt: str, max_tool_rounds: int = 5) -> str:
        if not self.choose_model:
            raise RuntimeError("No model selected.")

        plan_data = self.planner.create_plan(prompt)
        self._trace("Goal", plan_data["goal"])
        self._trace("Plan", "; ".join(plan_data["plan"]) if plan_data["plan"] else "No plan steps returned.")

        messages = [{"role": "user", "content": prompt}]
        tools = self.tool_repository.get_tool_definitions()
        observations: list[str] = []

        for round_num in range(max_tool_rounds + 1):
            data = self._chat(messages, tools=tools)
            assistant_message = self._extract_assistant_message(data)
            tool_calls = self._extract_tool_calls(assistant_message)

            if not tool_calls:
                label = "Agent" if round_num == 0 else "Agent (round %d)" % (round_num + 1)
                self._trace(label, "No further tool needed, answering directly")
                answer = self._extract_content(assistant_message)
                self._trace("Answer", answer)
                reflection = self.reflector.reflect(plan_data["goal"], observations, answer)
                self._trace("Reflection", reflection["reflection"])
                return answer

            self._trace(
                "Agent" if round_num == 0 else "Agent (round %d)" % (round_num + 1),
                f"Call tool(s): {[tc.get('function', {}).get('name') for tc in tool_calls]}",
            )

            messages.append(assistant_message)
            for tool_call in tool_calls:
                tool_name, tool_result = self._execute_tool_call(tool_call)
                self._trace("Tool", f"{tool_name}({tool_call.get('function', {}).get('arguments', {})})")
                self._trace("Observation", str(tool_result))
                observations.append(f"{tool_name} -> {tool_result}")
                messages.append(self._build_tool_result_message(tool_name, tool_result))

        # Ran out of rounds while the model kept requesting tools; ask once more for a final answer.
        final_data = self._chat(messages, tools=None)
        final_message = self._extract_assistant_message(final_data)
        answer = self._extract_content(final_message)
        self._trace("Answer", answer)
        reflection = self.reflector.reflect(plan_data["goal"], observations, answer)
        self._trace("Reflection", f"{reflection['reflection']} (reached max_tool_rounds={max_tool_rounds})")
        return answer
