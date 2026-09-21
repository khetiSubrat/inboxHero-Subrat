import json
import os
from datetime import datetime, timezone

LOG_PATH = "logs/gate_log.jsonl"

# Part 4 manifest: which actions are reversible vs irreversible, and why.
ACTION_MANIFEST = {
    "draft": {
        "reversible": True,
        "reason": "Only produces text in memory/draft.json. Nothing external happens; it can be rewritten or discarded.",
    },
    "archive": {
        "reversible": True,
        "reason": "Changes a disposition label only. Re-labeling undoes it.",
    },
    "defer": {
        "reversible": True,
        "reason": "Schedules a later look. No external effect occurs.",
    },
    "label": {
        "reversible": True,
        "reason": "Metadata only. Changing it again undoes it.",
    },
    "send": {
        "reversible": False,
        "reason": "Once written to outbox/, the recipient has it. A sent message cannot be unsent.",
    },
    "delete": {
        "reversible": False,
        "reason": "The mock mail store has no trash/undo, so a deleted message is gone for good.",
    },
}

IRREVERSIBLE_ACTIONS = {name for name, info in ACTION_MANIFEST.items() if not info["reversible"]}

# Escalation line: only irreversible actions (send, delete) are ever gated.
# Reversible actions (draft, archive, defer, label) run automatically -- asking
# approval for those would just train the user to rubber-stamp everything.
# Trade-off: a wrongly-archived message is possible in exchange for not asking
# the user to approve dozens of routine, reversible triage decisions.


class ActionGate:
    """Gates every irreversible action behind explicit approval or --dry-run."""

    def __init__(self, dry_run=False, auto_approve=False):
        self.dry_run = dry_run
        self.auto_approve = auto_approve  # non-interactive approval, for scripted/test runs only
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    def run(self, action, message_id, proposed, execute_fn):
        """
        action: one of ACTION_MANIFEST keys.
        message_id: the email this action concerns.
        proposed: human-readable description of what would happen.
        execute_fn: zero-arg callable performing the actual effect.
        Returns (decision, outcome); every call is logged regardless of outcome.
        """
        if action not in IRREVERSIBLE_ACTIONS:
            outcome = execute_fn()
            self._log(action, message_id, proposed, "auto (reversible)", outcome)
            return "auto", outcome

        if self.dry_run:
            print(f"[DRY-RUN] Would {action} for {message_id}: {proposed}")
            self._log(action, message_id, proposed, "dry_run", None)
            return "dry_run", None

        approved = self.auto_approve or input(
            f"Approve {action} for {message_id}? {proposed}\n[y/N]: "
        ).strip().lower() == "y"

        if not approved:
            print(f"Rejected: {action} for {message_id}")
            self._log(action, message_id, proposed, "rejected", None)
            return "rejected", None

        outcome = execute_fn()
        self._log(action, message_id, proposed, "approved", outcome)
        return "approved", outcome

    def _log(self, action, message_id, proposed, decision, outcome):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "message_id": message_id,
            "proposed": proposed,
            "decision": decision,
            "outcome": outcome,
        }
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
