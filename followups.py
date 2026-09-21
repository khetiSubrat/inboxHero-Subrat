"""
Part 8 capability: Follow-up tracking for sent messages nobody answered.

A thread whose most recent message is one Sam sent to someone else, with
nothing back since, means Sam is still waiting on a reply. Recomputed fresh
from the mail store every run -- not a hardcoded list.
"""

from datetime import datetime

OWNER = "sam@paperjet.io"


def find_open_followups(emails, now=None):
    now = now or datetime.now()
    threads = {}
    for e in emails:
        threads.setdefault(e.get("thread_id"), []).append(e)

    open_followups = []
    for thread_id, msgs in threads.items():
        if not thread_id:
            continue
        last = sorted(msgs, key=lambda m: m["timestamp"])[-1]
        if last.get("from") != OWNER or last.get("to") == OWNER:
            continue
        sent_at = datetime.fromisoformat(last["timestamp"])
        open_followups.append({
            "message_id": last["id"],
            "thread_id": thread_id,
            "subject": last.get("subject"),
            "sent_to": last.get("to"),
            "sent_at": last["timestamp"],
            "days_open": (now - sent_at).days,
        })
    return sorted(open_followups, key=lambda f: -f["days_open"])
