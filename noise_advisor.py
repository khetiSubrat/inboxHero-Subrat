"""
Part 8 capability: Noise / unsubscribe advisor.

Flags senders whose every message this run archived as pure automated noise
(receipts, digests, usage reports) -- recurring low-value senders worth
unsubscribing from, surfaced instead of buried one-by-one in ARCHIVE.
"""


def find_unsubscribe_candidates(emails, results, min_count=2):
    results_by_id = {r["id"]: r for r in results}
    by_sender = {}
    for e in emails:
        r = results_by_id.get(e["id"])
        if r is None:
            continue
        stats = by_sender.setdefault(e.get("from", ""), {"total": 0, "noise": 0, "subjects": []})
        stats["total"] += 1
        stats["subjects"].append(e.get("subject"))
        if r["disposition"] == "ARCHIVE" and r["classification"] == "AUTOMATED":
            stats["noise"] += 1

    candidates = [
        {"sender": sender, "message_count": s["total"], "sample_subjects": s["subjects"][:3]}
        for sender, s in by_sender.items()
        if s["total"] >= min_count and s["noise"] == s["total"]
    ]
    return sorted(candidates, key=lambda c: -c["message_count"])
