import json
from disposition import assign_dispositions, print_statistics, save_dispositions_to_file
from reply_agent import ReplyAgent


def draft_replies(emails, results, limit=None):
    """Part 3: draft a grounded reply for REPLY-disposition messages (optionally capped by `limit`)."""
    print("\n" + "=" * 70)
    print("PART 3: ANSWERING PROPERLY - Grounded Replies")
    print("=" * 70)

    agent = ReplyAgent(emails)
    reply_ids = [r["id"] for r in results if r["disposition"] == "REPLY"]
    if limit is not None:
        reply_ids = reply_ids[:limit]

    drafts = []
    for i, msg_id in enumerate(reply_ids, start=1):
        print(f"  [{i}/{len(reply_ids)}] drafting reply for {msg_id}...", flush=True)
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


def main():
    # Load inbox
    print("Loading emails from Docs/inbox.json...")
    with open('Docs/inbox.json', 'r') as f:
        emails = json.load(f)
    print(f"✓ Loaded {len(emails)} emails\n")

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


if __name__ == '__main__':
    try:
        main()
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except RuntimeError as e:
        print(f"Runtime Error: {e}")
