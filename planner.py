import json
import re


class Planner:
    """Turns a user request into a one-line goal plus a short step plan, via one model call."""

    def __init__(self, model, tool_names=None):
        self.model = model
        self.tool_names = tool_names or []

    def create_plan(self, prompt):
        tools_hint = (
            f"Available tools: {', '.join(self.tool_names)}."
            if self.tool_names
            else "No tools are available; answer directly."
        )
        planning_prompt = (
            "Restate the goal of the request below in one line, then give a short "
            "numbered plan (2-4 steps) to answer it. Respond ONLY as JSON: "
            '{"goal": "...", "plan": ["step 1", "step 2"]}.\n'
            f"{tools_hint}\n\nRequest: {prompt}"
        )
        goal, plan = prompt, []
        try:
            data = self.model._chat([{"role": "user", "content": planning_prompt}])
            content = data.get("message", {}).get("content", "")
            parsed = self._parse_json(content)
            goal = parsed.get("goal") or prompt
            plan = parsed.get("plan") or []
        except Exception:
            pass  # Fall back to the raw prompt as the goal with no plan steps.
        return {"goal": goal, "plan": plan}

    def _parse_json(self, text):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
