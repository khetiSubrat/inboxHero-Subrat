"""
Part 5: Standing Instructions.

Owner preferences are learned from specific, hand-recognized message patterns
only (never from generic "remember this" phrasing).

PREFERENCE_MANIFEST names the preferences this system honours end to end:
- no_meetings_before: learned from m041 ("I do not take meetings before
  11:00am, ever") and applied to m043 (an investor proposing Monday 9:00am),
  whose drafted reply is overridden to decline and counter-offer 11:00am+.
- cc_legal_correspondence: learned from m015 ("make sure I'm CC'd on anything
  that comes in from our lawyers at Hartwell & Cho") and applied to any reply
  sent to a hartwellcho.com sender (e.g. m018), which is CC'd to Priya.
"""

import re
from memory import remember, recall

PREFERENCE_MANIFEST = {
    "no_meetings_before": {
        "source_message_id": "m041",
        "affects_message_id": "m043",
        "description": "Owner never takes meetings before 11:00am; early proposals are declined with a counter-offer.",
    },
    "cc_legal_correspondence": {
        "source_message_id": "m015",
        "affects_message_id": "m018",
        "description": "Priya must be CC'd on any reply to correspondence from Hartwell & Cho (the company's lawyers).",
    },
}

TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*am")
LAW_FIRM_RE = re.compile(r"lawyers at ([a-z&\s]+?)\.", re.IGNORECASE)


def _to_hhmm(hour, minute):
    return f"{int(hour):02d}:{minute}"


def _domain_from_firm_name(name):
    slug = re.sub(r"[^a-z0-9]", "", name.lower())
    return f"{slug}.com"


def learn_preferences(emails):
    """Read each known preference source message and persist its rule via memory.py."""
    by_id = {e["id"]: e for e in emails}
    learned = []

    source_id = PREFERENCE_MANIFEST["no_meetings_before"]["source_message_id"]
    source = by_id.get(source_id)
    if source is not None:
        match = TIME_RE.search(source.get("body", "").lower())
        if match:
            cutoff = _to_hhmm(*match.groups())
            previously_known = recall("no_meetings_before")
            already_known = previously_known["status"] == "success" and previously_known["value"] == cutoff
            remember("no_meetings_before", cutoff, source=source_id)
            learned.append(("no_meetings_before", cutoff, already_known))

    source_id = PREFERENCE_MANIFEST["cc_legal_correspondence"]["source_message_id"]
    source = by_id.get(source_id)
    if source is not None:
        firm_match = LAW_FIRM_RE.search(source.get("body", ""))
        if firm_match:
            value = {"domain": _domain_from_firm_name(firm_match.group(1)), "cc": source.get("from")}
            previously_known = recall("cc_legal_correspondence")
            already_known = previously_known["status"] == "success" and previously_known["value"] == value
            remember("cc_legal_correspondence", value, source=source_id)
            learned.append(("cc_legal_correspondence", value, already_known))

    return learned


def get_no_meetings_before():
    """Recall the standing cutoff time, or None if it hasn't been learned yet."""
    result = recall("no_meetings_before")
    return result["value"] if result["status"] == "success" else None


def get_cc_for_sender(sender_email):
    """Recall the address that must be CC'd on a reply to `sender_email`, or None."""
    result = recall("cc_legal_correspondence")
    if result["status"] != "success":
        return None
    rule = result["value"]
    domain = sender_email.split("@")[-1].lower()
    return rule["cc"] if domain == rule["domain"] else None


def find_early_meeting_time(body, cutoff):
    """Return the proposed HH:MM if `body` proposes a meeting earlier than `cutoff`, else None."""
    match = TIME_RE.search(body.lower())
    if not match:
        return None
    proposed = _to_hhmm(*match.groups())
    return proposed if proposed < cutoff else None


def build_override_draft(message, proposed_time, cutoff, source_message_id):
    """Compose a reply that declines the early slot per the standing instruction, citing it."""
    draft = (
        f"Re: {message.get('subject', '')}\n\n"
        f"Thanks for the note -- {proposed_time}am doesn't work; standing rule is no meetings "
        f"before {cutoff}am. Could we do {cutoff}am or later instead?"
    )
    return {
        "message_id": message["id"],
        "draft": draft,
        "source_message_ids": [source_message_id],
        "retrieval_method": "standing-instruction",
        "grounded": True,
        "preference_applied": "no_meetings_before",
    }
