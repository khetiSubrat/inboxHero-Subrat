class Reflector:
    """Checks, via one model call, whether the final answer actually addresses the goal."""

    def __init__(self, model):
        self.model = model

    def reflect(self, goal, observations, answer):
        obs_text = "\n".join(observations) if observations else "(no tool calls were made)"
        reflection_prompt = (
            f"Goal: {goal}\nObservations:\n{obs_text}\nFinal answer: {answer}\n\n"
            "In one sentence, say whether the answer addresses the goal using the "
            "observations, or note what's missing."
        )
        try:
            data = self.model._chat([{"role": "user", "content": reflection_prompt}])
            text = data.get("message", {}).get("content", "").strip()
        except Exception as e:
            text = f"Reflection unavailable: {e}"
        return {"reflection": text or "No reflection generated."}
