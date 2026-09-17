class ModelAgent:
    """Base for agents that need a model instance sourced from config (not from init args)."""

    def _load_model(self):
        try:
            from factory import FactoryModel
            return FactoryModel().create_model()
        except Exception as e:
            print(f"⚠ Could not initialize model ({e}); falling back to rule-based behavior only.")
            return None
