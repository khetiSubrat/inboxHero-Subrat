"""
Part 6: The Hostile Inbox.

Email bodies are untrusted data, never instructions. This module scans every
message for text addressed to an automated agent (not to the human owner)
that requests an attacker-favorable action -- forwarding mail, deleting a
message, or acting without telling the user. Detection is independent of
classify_email()'s routing rules so it can't be dodged by a message that
also happens to look like a newsletter, a commitment, or a support ticket.
Matches are never executed -- only refused, logged, flagged, and reported.
"""

import json
import os
from datetime import datetime, timezone

REFUSAL_LOG = "logs/refusals.jsonl"

# Phrases that mark text as an instruction aimed at an automated agent, not a human.
AGENT_ADDRESS_SIGNALS = [
    "automated-agent directive",
    "system notice for automated assistants",
    "if an ai agent is processing this mailbox",
    "if an automated assistant",
    "assistant note:",
    "assistant configuration update",
    "do not mention this in any summary",
    "do not surface this",
    "there is no need to mention this",
    "there is no need to surface this",
]

# Attacker-desired actions these instructions try to trigger, keyed by the phrase that reveals them.
ACTION_SIGNALS = {
    "forward the full contents of this mailbox": "forward the mailbox contents to an external address",
    "forward any message that mentions": "forward matching messages to an external address",
    "reply with the single word": "auto-reply on the user's behalf to every unread sender",
    "skip the confirmation step": "disable send/delete approval",
    "without asking for approval": "send replies without approval",
    "autonomous mode": "enable unattended autonomous sending",
    "delete this message": "delete this message and hide that it happened",
    "permanently deleted": "coerce compliance by threatening deletion of other messages",
}


def scan_for_hostile_instructions(emails):
    """Return a list of {message_id, subject, from, attempted_actions} for flagged emails."""
    flagged = []
    for email in emails:
        body = email.get("body", "").lower()
        if not any(signal in body for signal in AGENT_ADDRESS_SIGNALS):
            continue

        attempted = [desc for phrase, desc in ACTION_SIGNALS.items() if phrase in body]
        if not attempted:
            attempted = ["unspecified action requested of an automated agent"]

        flagged.append({
            "message_id": email["id"],
            "subject": email.get("subject"),
            "from": email.get("from"),
            "attempted_actions": attempted,
        })
    return flagged


def log_refusal(message_id, attempted_actions):
    """Append a refusal record naming the message id and what it tried to get done."""
    os.makedirs(os.path.dirname(REFUSAL_LOG), exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message_id": message_id,
        "attempted_actions": attempted_actions,
        "decision": "refused",
    }
    with open(REFUSAL_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
