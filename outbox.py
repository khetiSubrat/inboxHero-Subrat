import json
import os

OUTBOX_DIR = "outbox"


def send_message(message_id, to, body, source_message_ids, cc=None):
    """The only place a 'send' effect happens: one file per message, in outbox/."""
    os.makedirs(OUTBOX_DIR, exist_ok=True)
    path = os.path.join(OUTBOX_DIR, f"{message_id}.json")
    with open(path, "w") as f:
        json.dump(
            {
                "message_id": message_id,
                "to": to,
                "cc": cc,
                "body": body,
                "source_message_ids": source_message_ids,
            },
            f,
            indent=2,
        )
    return path
