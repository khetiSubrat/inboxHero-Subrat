"""
Part 8 capability: Daily Digest.

Reads this run's own results/commitments (nothing hand-assembled) and renders
a short, skimmable summary: what happened, what needs Sam, what can wait.
"""


def build_digest(results, commitments):
    counts = {}
    for r in results:
        counts[r["disposition"]] = counts.get(r["disposition"], 0) + 1

    needs_you = [
        {"id": r["id"], "subject": r["subject"], "disposition": r["disposition"], "reason": r["reason"]}
        for r in results if r["disposition"] in ("REPLY", "ESCALATE")
    ]
    can_wait = [
        {"id": r["id"], "subject": r["subject"], "reason": r["reason"]}
        for r in results if r["disposition"] == "DEFER"
    ]
    upcoming = sorted((c for c in commitments if c["date"]), key=lambda c: c["date"])[:5]

    return {
        "totals_by_disposition": counts,
        "needs_you": needs_you,
        "can_wait": can_wait,
        "upcoming_commitments": upcoming,
    }


def print_digest(digest):
    print("What happened:", ", ".join(f"{k}={v}" for k, v in sorted(digest["totals_by_disposition"].items())))
    print(f"Needs you ({len(digest['needs_you'])}):")
    for item in digest["needs_you"][:10]:
        print(f"  • {item['id']:5s} | {item['subject']}")
    print(f"Can wait ({len(digest['can_wait'])}):")
    for item in digest["can_wait"][:10]:
        print(f"  • {item['id']:5s} | {item['subject']}")
    print("Upcoming commitments:")
    for c in digest["upcoming_commitments"]:
        print(f"  • {c['date']} {c['time'] or ''} | {c['title']} ({', '.join(c['source_message_ids'])})")
