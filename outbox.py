import json
import os

OUTBOX_DIR = "outbox"
DELETED_LOG = "model/deleted.json"


def send_message(message_id, to, body, source_message_ids):
    """The only place a 'send' effect happens: one file per message, in outbox/."""
    os.makedirs(OUTBOX_DIR, exist_ok=True)
    path = os.path.join(OUTBOX_DIR, f"{message_id}.json")
    with open(path, "w") as f:
        json.dump(
            {
                "message_id": message_id,
                "to": to,
                "body": body,
                "source_message_ids": source_message_ids,
            },
            f,
            indent=2,
        )
    return path


def delete_message(message_id):
    """Record a deletion. The mail store (Docs/inbox.json) is never mutated."""
    deleted = []
    if os.path.exists(DELETED_LOG):
        with open(DELETED_LOG) as f:
            deleted = json.load(f)
    deleted.append(message_id)
    with open(DELETED_LOG, "w") as f:
        json.dump(deleted, f, indent=2)
    return DELETED_LOG
