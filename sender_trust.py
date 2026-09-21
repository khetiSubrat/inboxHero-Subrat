"""
Part 8 capability: Sender trust, persisted across restarts.

Builds on the same memory.py used for Part 5 preferences and the Part 6
hostile-inbox scan: every BLOCK verdict increments that sender's incident
count in memory_store.json. A sender who crosses the threshold is flagged
for permanent distrust instead of being re-evaluated from scratch each run.
"""

from memory import remember, recall

THRESHOLD = 2


def update_sender_trust(results):
    incidents_this_run = {}
    for r in results:
        if r["disposition"] == "BLOCK":
            incidents_this_run[r["from"]] = incidents_this_run.get(r["from"], 0) + 1

    escalations = []
    for sender, count in incidents_this_run.items():
        key = f"trust_incidents:{sender}"
        prior = recall(key)
        total = (prior["value"] if prior["status"] == "success" else 0) + count
        remember(key, total, source="part8-sender-trust")
        if total >= THRESHOLD:
            escalations.append({"sender": sender, "total_incidents": total})
    return escalations
