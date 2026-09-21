"""
demo.py -- capability-scoped entry point that capabilities.json's "command"
field for every R1-R6 / X1-X4 entry actually runs.

    python demo.py --cap R1
    python demo.py --cap R3 --dry-run
    python demo.py --all --dry-run      # every capability, in manifest order

Each capability writes the same JSON artifact main.py's full run writes
(model/dispositions.json, model/draft.json, model/commitments.json, ...) and also
appends a tagged event to model/trace.jsonl, so a capability's evidence can be
checked in isolation. R4 (persistent preference) and X4 (persistent sender
trust) are the two capabilities that are meant to be run more than once --
their claim is specifically about what happens on a second, separate process.
"""

import argparse
import json

from disposition import assign_dispositions, print_statistics, save_dispositions_to_file
from reply_agent import ReplyAgent
from gate import ActionGate
from outbox import send_message
from preferences import (
    learn_preferences,
    get_no_meetings_before,
    get_cc_for_sender,
    find_early_meeting_time,
    build_override_draft,
    PREFERENCE_MANIFEST,
)
from guard_mail import scan_for_hostile_instructions, log_refusal
from commitments import extract_commitments, find_conflicts
from dashboard import build_dashboard, render_html
from digest import build_digest, print_digest
from followups import find_open_followups
from noise_advisor import find_unsubscribe_candidates
from sender_trust import update_sender_trust
from trace import trace_event

INBOX_PATH = "Docs/inbox.json"


def load_emails():
    with open(INBOX_PATH) as f:
        return json.load(f)


def _dispositions_with_hostile_override(emails, cap):
    """Shared by every cap: assign dispositions, then force BLOCK on hostile hits."""
    results, stats = assign_dispositions(emails)
    flagged = scan_for_hostile_instructions(emails)
    by_id = {r["id"]: r for r in results}
    for f in flagged:
        r = by_id.get(f["message_id"])
        if r is None:
            continue
        if r["disposition"] != "BLOCK":
            stats["by_disposition"][r["disposition"]] -= 1
            stats["by_disposition"]["BLOCK"] += 1
        r["disposition"] = "BLOCK"
        r["reason"] = "Hostile inbox: instruction addressed to an automated agent (" + "; ".join(f["attempted_actions"]) + ")"
        r["hostile"] = True
        r["attempted_actions"] = f["attempted_actions"]
    trace_event(cap, "decision", {"total": len(results), "rule_based": stats["rule_based"], "hostile_blocked": len(flagged)})
    return results, stats, flagged


def cap_r1(emails, dry_run):
    results, stats, _ = _dispositions_with_hostile_override(emails, "R1")
    print_statistics(results, stats)
    save_dispositions_to_file(results)
    print(f"undecided: {sum(1 for r in results if r['disposition'] is None)}")
    return results


def cap_r2(emails, dry_run):
    results, _, _ = _dispositions_with_hostile_override(emails, "R2")
    agent = ReplyAgent(emails)
    reply_ids = [r["id"] for r in results if r["disposition"] == "REPLY"]
    drafts = []
    for msg_id in reply_ids:
        draft = agent.draft_reply(msg_id)
        drafts.append(draft)
        trace_event("R2", "draft", {
            "message_id": msg_id,
            "grounded": draft["grounded"],
            "source_message_ids": draft.get("source_message_ids"),
        })
    with open("model/draft.json", "w") as f:
        json.dump(drafts, f, indent=2)
    print(f"drafted {sum(d['grounded'] for d in drafts)}, refused {sum(not d['grounded'] for d in drafts)}")
    m008 = next((d for d in drafts if d["message_id"] == "m008"), None)
    if m008:
        print(f"m008 -> grounded={m008['grounded']} source_message_ids={m008['source_message_ids']}")
        print(f"draft: {m008['draft']}")
    return drafts


def cap_r3(emails, dry_run):
    drafts = cap_r2(emails, dry_run)
    by_id = {e["id"]: e for e in emails}
    gate = ActionGate(dry_run=dry_run)
    results = []
    for d in drafts:
        if not d["grounded"]:
            continue
        to = by_id[d["message_id"]]["from"]
        cc = get_cc_for_sender(to)
        proposed = f"send to {to}" + (f" (cc {cc})" if cc else "") + f": {d['draft'][:120]}..."
        decision, outcome = gate.run(
            "send", d["message_id"], proposed,
            execute_fn=lambda d=d, to=to, cc=cc: send_message(d["message_id"], to, d["draft"], d["source_message_ids"], cc=cc),
        )
        trace_event("R3", "gate", {"message_id": d["message_id"], "proposed": proposed, "decision": decision})
        results.append({"message_id": d["message_id"], "decision": decision, "cc": cc})
    with open("model/send_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"outbox/ writes: {sum(1 for r in results if r['decision'] == 'approved')}")
    return results


def cap_r4(emails, dry_run):
    learned = learn_preferences(emails)
    for key, value, already_known in learned:
        verb = "recalled (already known)" if already_known else "learned new"
        print(f"{verb}: {key} = {value}")
        trace_event("R4", "preference", {"key": key, "value": value, "already_known": already_known})

    cutoff = get_no_meetings_before()
    m043 = next((e for e in emails if e["id"] == "m043"), None)
    if m043 and cutoff:
        proposed_time = find_early_meeting_time(m043["body"], cutoff)
        if proposed_time:
            source_id = PREFERENCE_MANIFEST["no_meetings_before"]["source_message_id"]
            draft = build_override_draft(m043, proposed_time, cutoff, source_id)
            print(f"m043 override -> {draft['draft']}")
            trace_event("R4", "override", {"message_id": "m043", "draft": draft["draft"], "source_message_ids": draft["source_message_ids"]})
    return learned


def cap_r5(emails, dry_run):
    flagged = scan_for_hostile_instructions(emails)
    for f in flagged:
        log_refusal(f["message_id"], f["attempted_actions"])
        trace_event("R5", "refusal", f)
        print(f"FLAGGED: {f['message_id']} attempted {'; '.join(f['attempted_actions'])}; not done, left in place.")
    with open("model/hostile_report.json", "w") as fp:
        json.dump(flagged, fp, indent=2)
    return flagged


def cap_r6(emails, dry_run):
    results, stats, flagged = _dispositions_with_hostile_override(emails, "R6")
    save_dispositions_to_file(results)
    with open("model/hostile_report.json", "w") as f:
        json.dump(flagged, f, indent=2)

    commitments = extract_commitments(emails)
    by_id = {e["id"]: e for e in emails}
    for c in commitments:
        missing = [mid for mid in c["source_message_ids"] if mid not in by_id]
        if missing:
            raise ValueError(f"Commitment '{c['id']}' cited unknown message ids: {missing}")
    conflicts = find_conflicts(commitments)
    with open("model/commitments.json", "w") as f:
        json.dump({"commitments": commitments, "conflicts": conflicts}, f, indent=2)

    dashboard = build_dashboard(emails)
    with open("model/dashboard.html", "w") as f:
        f.write(render_html(dashboard))

    trace_event("R6", "dashboard", {"commitments": len(commitments), "conflicts": len(conflicts)})
    print(f"wrote model/dashboard.html -- {len(commitments)} commitment(s), {len(conflicts)} conflict group(s)")
    for group in conflicts:
        print("  CONFLICT: " + " vs ".join(f"{c['title']} ({c['date']} {c['time']}, {c['source_message_ids']})" for c in group))
    return dashboard


def cap_x1(emails, dry_run):
    results, _, _ = _dispositions_with_hostile_override(emails, "X1")
    commitments = extract_commitments(emails)
    digest = build_digest(results, commitments)
    with open("model/digest.json", "w") as f:
        json.dump(digest, f, indent=2)
    print_digest(digest)
    trace_event("X1", "digest", {"needs_you": len(digest["needs_you"]), "can_wait": len(digest["can_wait"])})
    return digest


def cap_x2(emails, dry_run):
    followups = find_open_followups(emails)
    with open("model/followups.json", "w") as f:
        json.dump(followups, f, indent=2)
    for item in followups:
        print(f"{item['message_id']} | sent to {item['sent_to']}, {item['days_open']}d ago | {item['subject']}")
    trace_event("X2", "followups", {"count": len(followups)})
    return followups


def cap_x3(emails, dry_run):
    results, _, _ = _dispositions_with_hostile_override(emails, "X3")
    candidates = find_unsubscribe_candidates(emails, results)
    with open("model/unsubscribe_candidates.json", "w") as f:
        json.dump(candidates, f, indent=2)
    for c in candidates:
        print(f"{c['sender']} ({c['message_count']} messages, all noise)")
    trace_event("X3", "unsubscribe", {"count": len(candidates)})
    return candidates


def cap_x4(emails, dry_run):
    results, _, _ = _dispositions_with_hostile_override(emails, "X4")
    escalations = update_sender_trust(results)
    with open("model/sender_trust_escalations.json", "w") as f:
        json.dump(escalations, f, indent=2)
    if not escalations:
        print("no sender has crossed the trust threshold yet (run again to accumulate incidents)")
    for e in escalations:
        print(f"ESCALATE {e['sender']}: {e['total_incidents']} BLOCK incidents across runs -- recommend permanent block")
    trace_event("X4", "sender_trust", {"escalations": len(escalations)})
    return escalations


CAPS = {
    "R1": cap_r1, "R2": cap_r2, "R3": cap_r3, "R4": cap_r4,
    "R5": cap_r5, "R6": cap_r6,
    "X1": cap_x1, "X2": cap_x2, "X3": cap_x3, "X4": cap_x4,
}


def main():
    parser = argparse.ArgumentParser(description="Run one or all inboxHero capabilities.")
    parser.add_argument("--cap", choices=sorted(CAPS), help="capability id from capabilities.json")
    parser.add_argument("--all", action="store_true", help="run every capability, in manifest order")
    parser.add_argument("--dry-run", action="store_true", help="propose sends without writing to outbox/")
    args = parser.parse_args()

    if not args.cap and not args.all:
        parser.error("pass --cap R1..R6/X1..X4, or --all")

    emails = load_emails()
    for cap in (list(CAPS) if args.all else [args.cap]):
        print(f"\n=== {cap}: {CAPS[cap].__doc__ or cap} ===")
        CAPS[cap](emails, args.dry_run)


if __name__ == "__main__":
    main()
