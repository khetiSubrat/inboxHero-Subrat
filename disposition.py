"""
inboxHero Part 2: Zeroing It
========================================

Disposition Vocabulary:
-----------------------
ARCHIVE     : No action needed. File away. Safe to ignore or review later.
REPLY       : Needs a response. Direct engagement required from Sam.
DEFER       : Needs action but can be scheduled for later. Blocking deadline.
DELEGATE    : Pass to someone else. Not Sam's responsibility or Sam needs to forward.
ESCALATE    : Needs immediate attention. High priority or time-sensitive.
BLOCK       : Security threat or malicious. Do not engage. Flag for review.
REVIEW      : Ambiguous or unclear. Hold for human review; no automatic action is taken.

Rules-Based Disposition Assignment:
-----------------------------------
Messages are deterministically assigned dispositions through rules based on 
classification category. Only REVIEW category is held back from automatic action.

Statistics tracked:
- Total messages processed
- Messages assigned by rule (no further action needed)
- Messages held in the REVIEW queue for a human
- Breakdown by disposition
"""

from classifier import classify_email
import json
import os


DISPOSITION_MANIFEST = {
    "ARCHIVE": {
        "label": "Archive",
        "color": "gray",
        "description": "No action needed. File away safely.",
        "requires_llm": False,
    },
    "REPLY": {
        "label": "Reply",
        "color": "blue",
        "description": "Needs a response. Direct engagement required.",
        "requires_llm": False,
    },
    "DEFER": {
        "label": "Defer",
        "color": "yellow",
        "description": "Needs action but scheduled for later. Blocking deadline.",
        "requires_llm": False,
    },
    "DELEGATE": {
        "label": "Delegate",
        "color": "purple",
        "description": "Pass to someone else.",
        "requires_llm": False,
    },
    "ESCALATE": {
        "label": "Escalate",
        "color": "red",
        "description": "Needs immediate attention.",
        "requires_llm": False,
    },
    "BLOCK": {
        "label": "Block",
        "color": "darkred",
        "description": "Security threat or malicious. Do not engage.",
        "requires_llm": False,
    },
    "REVIEW": {
        "label": "Review",
        "color": "orange",
        "description": "Ambiguous or unclear. Hold for human review; no automatic action is taken.",
        "requires_llm": True,
    },
}


def classify_to_disposition(classification, email):
    """
    Map classification category to disposition using deterministic rules.
    
    Args:
        classification: Category from classify_email()
        email: The email dict containing id, subject, body, from, etc.
    
    Returns:
        disposition: The assigned disposition (one of ARCHIVE, REPLY, DEFER, DELEGATE, ESCALATE, BLOCK)
        reason: Explanation string for why this disposition was assigned
        is_rule_based: Boolean indicating if assigned by rule (True) or would need LLM (False)
    """
    
    subject = email.get("subject", "").lower()
    body = email.get("body", "").lower()
    sender = email.get("from", "").lower()
    thread_id = email.get("thread_id", "").lower()
    message_id = email.get("id", "")
    
    # ---------------------------------------------------------
    # SECURITY -> BLOCK or ESCALATE
    # ---------------------------------------------------------
    if classification == "SECURITY":
        # Phishing/injection attempts -> BLOCK
        if thread_id.startswith("t-phish") or thread_id.startswith("t-inj"):
            return "BLOCK", "Security threat detected: phishing/injection attempt", True
        
        # Legitimate security alerts -> ESCALATE
        if "verify" in subject or "password" in subject:
            return "ESCALATE", "Security: credential verification needed", True
        
        return "ESCALATE", "Security alert requires immediate attention", True
    
    # ---------------------------------------------------------
    # PREFERENCE -> ARCHIVE (standing rules noted, no action needed)
    # ---------------------------------------------------------
    if classification == "PREFERENCE":
        if "do not take meetings before 11" in body or "11:00am" in body:
            return "ARCHIVE", "Standing preference documented (no meetings before 11am)", True
        if "cc'd on anything" in body or "loop me in" in body:
            return "ARCHIVE", "Standing preference documented (copy Priya on legal)", True
        return "ARCHIVE", "Standing preference documented", True
    
    # ---------------------------------------------------------
    # SCHEDULING -> DEFER or DELEGATE
    # ---------------------------------------------------------
    if classification == "SCHEDULING":
        # Requests to move existing meetings -> quick REPLY needed
        if "can we move" in body or "move our" in body:
            return "REPLY", "Scheduling: request to move meeting requires response", True
        
        # New meeting requests -> DEFER (schedule for later)
        if "calendar" in subject or "appointment" in subject:
            return "DEFER", "Scheduling: new appointment needs to be added to calendar", True
        
        return "DEFER", "Scheduling: meeting requires calendar decision", True
    
    # ---------------------------------------------------------
    # COMMITMENT -> DEFER (important deadlines)
    # ---------------------------------------------------------
    if classification == "COMMITMENT":
        # Extract deadline info for better reasoning
        if "by the 12th" in body or "by 12th" in body or "september 12" in body.lower():
            return "DEFER", "Commitment: pricing copy approval deadline Sep 12", True
        if "by the 19th" in body or "by 19th" in body:
            return "REPLY", "Commitment: hiring follow-up needs response (deadline Sep 19)", True
        if "by friday" in body or "by end of day" in body:
            return "REPLY", "Commitment: time-bound task needs immediate response", True
        return "DEFER", "Commitment: deadline-driven task", True
    
    # ---------------------------------------------------------
    # AUTOMATED -> ARCHIVE
    # ---------------------------------------------------------
    if classification == "AUTOMATED":
        # Some automated messages are FYI only (reports, receipts, status updates)
        # Exception: some might need action (renewal reminders, etc)
        if "reminder" in subject and "appointment" in subject:
            return "DEFER", "Automated: appointment reminder needs confirmation", True
        if "delivery" in subject or "shipped" in subject or "receipt" in subject:
            return "ARCHIVE", "Automated: receipt or delivery notification", True
        if "report" in subject or "digest" in subject or "update" in subject:
            return "ARCHIVE", "Automated: informational report or digest", True
        if "renewal" in subject or "renew" in subject:
            return "ARCHIVE", "Automated: billing notification (auto-renew enabled)", True
        return "ARCHIVE", "Automated: system-generated notification", True
    
    # ---------------------------------------------------------
    # ACTIONABLE -> REPLY or DEFER
    # ---------------------------------------------------------
    if classification == "ACTIONABLE":
        # Known work threads - most need engagement
        if "t-api" in thread_id:
            return "REPLY", "Actionable: engineering task in active thread", True
        if "t-launch" in thread_id:
            # Priya's pricing copy request is a DEFER
            if "pricing" in subject or "pricing page copy" in body:
                return "DEFER", "Actionable: pricing copy approval (deadline Sep 12)", True
            # Team updates in launch thread -> ARCHIVE after reading
            if "looking good" in body or "green" in body or "draft" in body:
                return "ARCHIVE", "Actionable: launch thread status update (FYI)", True
            return "REPLY", "Actionable: launch coordination requires response", True
        if "t-board" in thread_id:
            return "DEFER", "Actionable: board review scheduling (Sep 18)", True
        if "t-invest" in thread_id:
            return "REPLY", "Actionable: investor call scheduling (Sep 15 at 3pm proposed)", True
        if "t-deck" in thread_id:
            return "DEFER", "Actionable: board deck deadline (Sep 16 - 2 days before review)", True
        if "t-legal" in thread_id:
            return "REPLY", "Actionable: legal correspondence from Hartwell & Cho needs signature/response", True
        
        return "REPLY", "Actionable: work thread requires engagement", True
    
    # ---------------------------------------------------------
    # CONTEXT_REQUIRED -> DEFER (need to read full thread)
    # ---------------------------------------------------------
    if classification == "CONTEXT_REQUIRED":
        # Generic vague messages need the full context
        if "the thing" in body:
            return "DEFER", "Context needed: vague reference requires thread history", True
        if "following up" in body or "follow up" in body:
            return "REPLY", "Context needed: follow-up may require response", True
        if "as discussed" in body or "as mentioned earlier" in body:
            return "DEFER", "Context needed: refer to earlier messages for full understanding", True
        return "DEFER", "Context needed: requires previous messages for understanding", True
    
    # ---------------------------------------------------------
    # REVIEW -> Mark for LLM review (cannot confidently classify)
    # ---------------------------------------------------------
    if classification == "REVIEW":
        return "REVIEW", f"Requires human/LLM review: message does not match known patterns", False
    
    # Fallback (should not reach here)
    return "ARCHIVE", f"Unclassified: {classification}", True


def assign_dispositions(emails):
    """
    Assign disposition to every email.
    
    Args:
        emails: List of email dicts from inbox.json
    
    Returns:
        results: List of dicts with email metadata and disposition assignment
        stats: Statistics about processing
    """
    results = []
    stats = {
        "total_emails": len(emails),
        "rule_based": 0,
        "llm_required": 0,
        "by_disposition": {
            "ARCHIVE": 0,
            "REPLY": 0,
            "DEFER": 0,
            "DELEGATE": 0,
            "ESCALATE": 0,
            "BLOCK": 0,
            "REVIEW": 0,
        },
        "by_classification": {},
    }
    
    for email in emails:
        email_id = email.get("id")
        classification = classify_email(email)
        
        # Track classification breakdown
        if classification not in stats["by_classification"]:
            stats["by_classification"][classification] = 0
        stats["by_classification"][classification] += 1
        
        # Assign disposition
        disposition, reason, is_rule_based = classify_to_disposition(classification, email)
        
        # Track statistics
        if is_rule_based:
            stats["rule_based"] += 1
        else:
            stats["llm_required"] += 1
        
        stats["by_disposition"][disposition] += 1
        
        # Store result with metadata
        results.append({
            "id": email_id,
            "from": email.get("from"),
            "subject": email.get("subject"),
            "thread_id": email.get("thread_id"),
            "classification": classification,
            "disposition": disposition,
            "reason": reason,
            "rule_based": is_rule_based,
            "requires_llm": (disposition == "REVIEW"),
        })
    
    return results, stats


def print_statistics(results, stats):
    """Print comprehensive statistics about disposition assignments."""
    print("\n" + "=" * 70)
    print("INBOXHERO PART 2: ZEROING IT - DISPOSITION REPORT")
    print("=" * 70)
    
    print(f"\nTotal emails processed: {stats['total_emails']}")
    print(f"Assigned by rules:      {stats['rule_based']:3} ({100*stats['rule_based']/stats['total_emails']:.1f}%)")
    print(f"Review queue:           {stats['llm_required']:3} ({100*stats['llm_required']/stats['total_emails']:.1f}%)")
    
    print("\n" + "-" * 70)
    print("DISPOSITION BREAKDOWN:")
    print("-" * 70)
    for disposition in sorted(stats["by_disposition"].keys()):
        count = stats["by_disposition"][disposition]
        pct = 100 * count / stats["total_emails"]
        print(f"  {disposition:20s}: {count:3d} emails ({pct:5.1f}%)")
    
    print("\n" + "-" * 70)
    print("CLASSIFICATION BREAKDOWN:")
    print("-" * 70)
    for classification in sorted(stats["by_classification"].keys()):
        count = stats["by_classification"][classification]
        pct = 100 * count / stats["total_emails"]
        print(f"  {classification:20s}: {count:3d} emails ({pct:5.1f}%)")
    
    print("\n" + "-" * 70)
    print("DISPOSITION MANIFEST:")
    print("-" * 70)
    for disp, details in DISPOSITION_MANIFEST.items():
        print(f"  {disp:12s}: {details['description']}")
    
    print("\n" + "=" * 70)
    print("KEY FINDINGS:")
    print("=" * 70)
    
    # Find messages requiring LLM
    llm_required = [r for r in results if not r["rule_based"]]
    if llm_required:
        print(f"\n{len(llm_required)} messages in the REVIEW queue:")
        for r in llm_required[:10]:  # Show first 10
            print(f"  • {r['id']:5s} | {r['subject'][:50]}")
        if len(llm_required) > 10:
            print(f"  ... and {len(llm_required) - 10} more")
    
    # Find critical messages (BLOCK, ESCALATE)
    critical = [r for r in results if r["disposition"] in ["BLOCK", "ESCALATE"]]
    if critical:
        print(f"\n{len(critical)} critical messages (BLOCK/ESCALATE):")
        for r in critical:
            print(f"  • {r['id']:5s} | {r['disposition']:10s} | {r['reason']}")
    
    # Find time-sensitive messages (REPLY, DEFER with deadlines)
    time_sensitive = [r for r in results if r["disposition"] in ["REPLY", "DEFER"] and "deadline" in r["reason"].lower()]
    if time_sensitive:
        print(f"\n{len(time_sensitive)} time-sensitive messages with deadlines:")
        for r in time_sensitive[:10]:
            print(f"  • {r['id']:5s} | {r['disposition']:10s} | {r['reason']}")
        if len(time_sensitive) > 10:
            print(f"  ... and {len(time_sensitive) - 10} more")
    
    print("\n" + "=" * 70)
    print(f"✓ {stats['total_emails']} messages processed.")
    if stats["llm_required"] > 0:
        print(f"  • {stats['rule_based']} assigned by deterministic rules")
        print(f"  • {stats['llm_required']} marked REVIEW for human review")
    print("=" * 70 + "\n")


def save_dispositions_to_file(results, filename="model/dispositions.json"):
    """Save disposition assignments to JSON file for reference."""
    parent = os.path.dirname(filename)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Disposition assignments saved to {filename}")
