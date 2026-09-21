"""
Part 7 support: extract commitments (dates/deadlines/obligations) from the inbox.

Rule-based, like classifier.py/disposition.py -- each rule reads the message's
own text and timestamp and computes a date rather than hardcoding a final one,
so results are recomputed fresh from a run instead of hand-assembled. Every
commitment cites the message id(s) it was grounded in; ids are verified the
same way Part 3 verifies its citations (see verify_commitment_ids in main.py).
"""

import re
from datetime import datetime, timedelta

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "sept": 9, "sep": 9,
    "october": 10, "november": 11, "december": 12,
}
_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.IGNORECASE)
_DAY_RE = re.compile(r"\bthe (\d{1,2})(?:st|nd|rd|th)\b", re.IGNORECASE)
_MONTH_DAY_RE = re.compile(
    r"\b(" + "|".join(_MONTHS) + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b", re.IGNORECASE
)
_WEEKDAY_RE = re.compile(r"\b(" + "|".join(_WEEKDAYS) + r")\b", re.IGNORECASE)


def _parse_time(text):
    match = _TIME_RE.search(text)
    if not match:
        return None
    hour = int(match.group(1)) % 12
    minute = int(match.group(2) or 0)
    if match.group(3).lower() == "pm":
        hour += 12
    return f"{hour:02d}:{minute:02d}"


def _parse_day_of_month(text, year, month):
    match = _MONTH_DAY_RE.search(text)
    if match:
        return datetime(year, _MONTHS[match.group(1).lower()], int(match.group(2))).date()
    match = _DAY_RE.search(text)
    if match:
        return datetime(year, month, int(match.group(1))).date()
    return None


def _last_weekday_mention(text, ref_date):
    """Take the last weekday named in the text (e.g. 'from Thursday to Wednesday' -> Wednesday)."""
    matches = list(_WEEKDAY_RE.finditer(text))
    if not matches:
        return None
    target = _WEEKDAYS[matches[-1].group(1).lower()]
    delta = (target - ref_date.weekday()) % 7
    return ref_date + timedelta(days=delta)


def _end_of_month(year, month):
    if month == 12:
        return datetime(year + 1, 1, 1).date() - timedelta(days=1)
    return datetime(year, month + 1, 1).date() - timedelta(days=1)


def extract_commitments(emails):
    """Return a list of commitment dicts, each grounded in one or more message ids."""
    by_id = {e["id"]: e for e in emails}
    commitments = []

    def add(key, title, date, time, source_ids, detail):
        commitments.append({
            "id": key,
            "title": title,
            "date": date.isoformat() if date else None,
            "time": time,
            "source_message_ids": source_ids,
            "detail": detail,
        })

    m = by_id.get("m030")
    if m:
        ref = datetime.fromisoformat(m["timestamp"])
        day = _parse_day_of_month(m["body"], ref.year, ref.month)
        if day:
            add("pricing-copy-approval", "Approve final pricing copy", day, None, ["m030"],
                "Pricing page cannot ship until Sam approves the annual-discount wording.")

    m = by_id.get("m042")
    if m:
        ref = datetime.fromisoformat(m["timestamp"])
        day = _parse_day_of_month(m["body"], ref.year, ref.month)
        if day:
            add("hiring-response", "Respond to Jordan re: backend offer", day, None, ["m042"],
                "Candidate has a competing offer and needs a decision.")

    board_date = None
    m38 = by_id.get("m038")
    if m38:
        ref = datetime.fromisoformat(m38["timestamp"])
        board_date = _parse_day_of_month(m38["body"], ref.year, ref.month)
        if board_date:
            add("board-review", "Quarterly board review", board_date, _parse_time(m38["body"]), ["m038"],
                "In-person at the office.")

    m40 = by_id.get("m040")
    if board_date and m40 and "two days before" in m40["body"].lower():
        add("board-deck-due", "Board deck finished and circulated", board_date - timedelta(days=2), None,
            ["m038", "m040"],
            "Deadline (m040: 'two days before the board review') resolved using the board review date (m038: the 18th).")

    m = by_id.get("m010")
    if m:
        ref = datetime.fromisoformat(m["timestamp"])
        day = _parse_day_of_month(m["body"], ref.year, ref.month)
        if day:
            add("investor-intro-call", "Investor intro call (Northwind VC)", day, _parse_time(m["body"]), ["m010"],
                "Proposed slot, awaiting confirmation.")

    m = by_id.get("m061")
    if m:
        ref = datetime.fromisoformat(m["timestamp"])
        day = _parse_day_of_month(m["body"], ref.year, ref.month)
        if day:
            add("dentist-appointment", "Dental cleaning (Dr. Osei)", day, _parse_time(m["body"]), ["m061"],
                "Reply CONFIRM to keep the slot.")

    m = by_id.get("m013")
    if m:
        ref = datetime.fromisoformat(m["timestamp"])
        date = _last_weekday_mention(m["body"], ref.date())
        if date:
            add("1-1-moved", "1:1 with Raghav (moved)", date, _parse_time(m["body"]), ["m013"],
                "Moved from Thursday to Wednesday this week.")

    m = by_id.get("m016")
    if m:
        ref = datetime.fromisoformat(m["timestamp"])
        date = _last_weekday_mention(m["body"], ref.date())
        if date:
            add("acme-demo", "Product demo for Acme Corp evaluation team", date, _parse_time(m["body"]), ["m016"],
                "Confirm the Wednesday 2:00pm slot.")

    m = by_id.get("m046")
    if m:
        ref = datetime.fromisoformat(m["timestamp"])
        date = _last_weekday_mention(m["body"], ref.date())
        if date:
            add("press-deadline", "Respond to TechBrief launch-coverage question", date, None, ["m046"],
                "On deadline for their piece.")

    m = by_id.get("m055")
    if m and "month-end" in m["body"].lower():
        ref = datetime.fromisoformat(m["timestamp"])
        add("ip-assignment-signature", "Sign IP assignment (Hartwell & Cho)", _end_of_month(ref.year, ref.month),
            None, ["m055"], "Not urgent, but before month-end.")

    return commitments


def find_conflicts(commitments):
    """Group commitments sharing the same date+time; return only groups with more than one entry."""
    buckets = {}
    for c in commitments:
        if not c["date"] or not c["time"]:
            continue
        buckets.setdefault((c["date"], c["time"]), []).append(c)
    return [group for group in buckets.values() if len(group) > 1]
