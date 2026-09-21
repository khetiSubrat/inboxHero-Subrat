"""
Part 8 capability (Tier A): one lookup, one output.

Lists every unread message from a single given sender. No disposition, no
drafting, no persisted state -- the simplest possible read-only query over
the inbox, included alongside the B/C-tier capabilities to show the floor
as well as the ceiling.
"""


def find_unread_from_sender(emails, sender):
    return [
        {"id": e["id"], "subject": e.get("subject"), "timestamp": e.get("timestamp")}
        for e in emails
        if e.get("from") == sender and e.get("unread")
    ]
