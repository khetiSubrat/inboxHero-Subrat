import json
import sys
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


def apply_standing_instructions(emails):
    """Part 5: learn owner preferences (persisted via memory.py) so they survive a restart."""
    print("\n" + "=" * 70)
    print("PART 5: STANDING INSTRUCTIONS")
    print("=" * 70)

    learned = learn_preferences(emails)
    if not learned:
        print("No standing instructions found.\n")
        return

    for key, value, already_known in learned:
        source_id = PREFERENCE_MANIFEST[key]["source_message_id"]
        verb = "Recalled" if already_known else "Learned new"
        symbol = "↺" if already_known else "✓"
        print(f"{symbol} {verb} standing instruction from {source_id} ({key}): {value}")
    print()


def draft_replies(emails, results, limit=None):
    """Part 3: draft a grounded reply for REPLY-disposition messages (optionally capped by `limit`)."""
    print("\n" + "=" * 70)
    print("PART 3: ANSWERING PROPERLY - Grounded Replies")
    print("=" * 70)

    by_id = {e["id"]: e for e in emails}
    agent = ReplyAgent(emails)
    cutoff = get_no_meetings_before()
    reply_ids = [r["id"] for r in results if r["disposition"] == "REPLY"]
    if limit is not None:
        reply_ids = reply_ids[:limit]

    drafts = []
    for i, msg_id in enumerate(reply_ids, start=1):
        print(f"  [{i}/{len(reply_ids)}] drafting reply for {msg_id}...", flush=True)

        message = by_id[msg_id]
        proposed_time = find_early_meeting_time(message.get("body", ""), cutoff) if cutoff else None
        if proposed_time:
            source_id = PREFERENCE_MANIFEST["no_meetings_before"]["source_message_id"]
            draft = build_override_draft(message, proposed_time, cutoff, source_id)
            print(f"    standing instruction applied: no meetings before {cutoff}am overrides proposed {proposed_time}am")
        else:
            draft = agent.draft_reply(msg_id)
        drafts.append(draft)

        print(f"    retrieval: {draft['retrieval_method']} | grounded: {draft['grounded']}")
        if draft["grounded"]:
            print(f"    source_message_ids: {draft['source_message_ids']}")
            print(f"    draft: {draft['draft']}\n")
        else:
            print(f"    reason: {draft['reason']}\n")

    grounded = [d for d in drafts if d["grounded"]]
    refused = [d for d in drafts if not d["grounded"]]
    print(f"✓ {len(grounded)} drafted, {len(refused)} refused (no grounding found)\n")

    return drafts


def send_replies(emails, drafts, dry_run):
    """Part 4: gate every send (irreversible) behind approval or --dry-run."""
    print("\n" + "=" * 70)
    print("PART 4: THE THINGS YOU CANNOT UNDO - Gated Sending")
    print("=" * 70)

    by_id = {e["id"]: e for e in emails}
    gate = ActionGate(dry_run=dry_run)
    results = []

    for d in drafts:
        if not d["grounded"]:
            continue
        message_id = d["message_id"]
        to = by_id[message_id]["from"]
        cc = get_cc_for_sender(to)
        proposed = f"send to {to}" + (f" (cc {cc})" if cc else "") + f" citing {d['source_message_ids']}: {d['draft'][:200]}..."

        decision, outbox_path = gate.run(
            "send",
            message_id,
            proposed,
            execute_fn=lambda d=d, to=to, cc=cc: send_message(d["message_id"], to, d["draft"], d["source_message_ids"], cc=cc),
        )
        results.append({"message_id": message_id, "decision": decision, "outbox_path": outbox_path, "cc": cc})

    return results


def main(dry_run=False):
    # Load inbox
    print("Loading emails from Docs/inbox.json...")
    with open('Docs/inbox.json', 'r') as f:
        emails = json.load(f)
    print(f"✓ Loaded {len(emails)} emails\n")

    # Part 5: Learn/recall standing instructions before anything is drafted
    apply_standing_instructions(emails)

    # Part 2: Assign dispositions to all emails
    print("=" * 70)
    print("PART 2: ZEROING IT - Assigning Dispositions")
    print("=" * 70)

    results, stats = assign_dispositions(emails)

    # Verify every message has a disposition
    unassigned = [r for r in results if r["disposition"] is None]
    if unassigned:
        print(f"ERROR: {len(unassigned)} messages without disposition!")
        for r in unassigned:
            print(f"  {r['id']}: {r['subject']}")
        return

    print(f"✓ Verification passed: All {len(results)} messages have dispositions\n")

    # Print statistics
    print_statistics(results, stats)

    # Save to file
    save_dispositions_to_file(results)

    # Part 3: Draft grounded replies for REPLY-disposition messages
    drafts = draft_replies(emails, results, limit=None)
    with open("draft.json", "w") as f:
        json.dump(drafts, f, indent=2)
    print("✓ Saved drafts to draft.json")

    # Part 4: Gate every send behind approval or --dry-run
    send_results = send_replies(emails, drafts, dry_run=dry_run)
    with open("model/send_results.json", "w") as f:
        json.dump(send_results, f, indent=2)
    print("✓ Saved send decisions to model/send_results.json (full log: logs/gate_log.jsonl)")


if __name__ == '__main__':
    dry_run = "--dry-run" in sys.argv
    try:
        main(dry_run=dry_run)
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except RuntimeError as e:
        print(f"Runtime Error: {e}")
