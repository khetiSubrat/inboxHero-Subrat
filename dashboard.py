"""
Part 7: The Dashboard.

Renders one three-pane view from a completed run's own JSON artifacts
(model/dispositions.json, draft.json, model/send_results.json,
model/hostile_report.json, model/commitments.json). Nothing here is
hand-assembled -- rerunning main.py regenerates every input file, and
this module only reads and formats them.

Panes:
  1. Pending actions -- every irreversible action the system proposed under
     the Part 4 gate, with why it needs a human (from gate.ACTION_MANIFEST).
  2. Flagged -- hostile instructions (Part 6), phishing/security blocks, and
     replies the system refused to draft because nothing grounded them.
  3. Commitments -- dates/deadlines extracted in Part 7, as a calendar,
     with same-slot conflicts called out instead of listed side by side.
"""

import json
from html import escape

from gate import ACTION_MANIFEST

INBOX_PATH = "Docs/inbox.json"
DISPOSITIONS_PATH = "model/dispositions.json"
DRAFT_PATH = "draft.json"
SEND_RESULTS_PATH = "model/send_results.json"
HOSTILE_REPORT_PATH = "model/hostile_report.json"
COMMITMENTS_PATH = "model/commitments.json"


def _load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def _pending_actions(emails_by_id, drafts_by_id, send_results):
    """Pane 1: every gated 'send' this run proposed, and why it needs a human."""
    why = ACTION_MANIFEST["send"]["reason"]
    rows = []
    for r in send_results:
        d = drafts_by_id.get(r["message_id"])
        if d is None:
            continue
        to = emails_by_id.get(r["message_id"], {}).get("from", "?")
        proposed = f"send to {to}" + (f" (cc {r['cc']})" if r.get("cc") else "") + f": {d['draft'][:120]}..."
        rows.append({
            "message_id": r["message_id"],
            "proposed_action": proposed,
            "why_needs_human": why,
            "status": r["decision"],
        })
    return rows


def _flagged(emails_by_id, dispositions, drafts, hostile_flagged):
    """Pane 2: hostile instructions, phishing/security blocks, and ungrounded drafts."""
    rows = []
    seen = set()

    for f in hostile_flagged:
        rows.append({
            "message_id": f["message_id"],
            "attempted": "; ".join(f["attempted_actions"]),
            "system_did": "refused; logged to logs/refusals.jsonl; disposition forced to BLOCK; left in place",
        })
        seen.add(f["message_id"])

    for r in dispositions:
        if r["id"] in seen or r["disposition"] != "BLOCK":
            continue
        if "phishing" not in r["reason"].lower() and "security" not in r["reason"].lower():
            continue
        rows.append({
            "message_id": r["id"],
            "attempted": r["reason"],
            "system_did": "blocked; no reply drafted or sent",
        })
        seen.add(r["id"])

    for d in drafts:
        if d["grounded"] or d["message_id"] in seen:
            continue
        subject = emails_by_id.get(d["message_id"], {}).get("subject", "")
        rows.append({
            "message_id": d["message_id"],
            "attempted": f"requested reply: \"{subject}\"",
            "system_did": d["reason"],
        })
        seen.add(d["message_id"])

    return rows


def build_dashboard(emails=None):
    """Assemble the three panes from this run's saved JSON artifacts."""
    if emails is None:
        emails = _load(INBOX_PATH, [])
    emails_by_id = {e["id"]: e for e in emails}

    dispositions = _load(DISPOSITIONS_PATH, [])
    drafts = _load(DRAFT_PATH, [])
    drafts_by_id = {d["message_id"]: d for d in drafts}
    send_results = _load(SEND_RESULTS_PATH, [])
    hostile_flagged = _load(HOSTILE_REPORT_PATH, [])
    commitments_data = _load(COMMITMENTS_PATH, {"commitments": [], "conflicts": []})

    return {
        "pending_actions": _pending_actions(emails_by_id, drafts_by_id, send_results),
        "flagged": _flagged(emails_by_id, dispositions, drafts, hostile_flagged),
        "commitments": commitments_data["commitments"],
        "conflicts": commitments_data["conflicts"],
    }


def _conflict_ids(conflicts):
    ids = set()
    for group in conflicts:
        for c in group:
            ids.add(c["id"])
    return ids


def render_html(data):
    pending_rows = "".join(
        f"<tr><td>{escape(r['message_id'])}</td><td>{escape(r['proposed_action'])}</td>"
        f"<td>{escape(r['why_needs_human'])}</td><td>{escape(r['status'])}</td></tr>"
        for r in data["pending_actions"]
    ) or "<tr><td colspan='4'><em>None</em></td></tr>"

    flagged_rows = "".join(
        f"<tr><td>{escape(r['message_id'])}</td><td>{escape(r['attempted'])}</td>"
        f"<td>{escape(r['system_did'])}</td></tr>"
        for r in data["flagged"]
    ) or "<tr><td colspan='3'><em>None</em></td></tr>"

    conflict_ids = _conflict_ids(data["conflicts"])
    commitment_rows = "".join(
        f"<tr class=\"{'conflict' if c['id'] in conflict_ids else ''}\">"
        f"<td>{escape(c['date'] or '')}</td><td>{escape(c['time'] or '')}</td>"
        f"<td>{escape(c['title'])}</td><td>{escape(', '.join(c['source_message_ids']))}</td>"
        f"<td>{escape(c['detail'])}</td></tr>"
        for c in sorted(data["commitments"], key=lambda c: (c["date"] or "", c["time"] or ""))
    ) or "<tr><td colspan='5'><em>None</em></td></tr>"

    conflict_blocks = "".join(
        "<div class='conflict-block'>⚠ Conflict at {date} {time}: {titles}</div>".format(
            date=escape(group[0]["date"]), time=escape(group[0]["time"]),
            titles=escape(" vs ".join(f"{c['title']} ({', '.join(c['source_message_ids'])})" for c in group)),
        )
        for group in data["conflicts"]
    ) or "<p><em>No conflicts.</em></p>"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>inboxHero Dashboard</title>
<style>
  body {{ font-family: -apple-system, sans-serif; margin: 2rem; color: #1a1a1a; }}
  h1 {{ font-size: 1.4rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 2.5rem; border-bottom: 2px solid #ddd; padding-bottom: .3rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: .75rem; }}
  th, td {{ border: 1px solid #ddd; padding: .5rem .6rem; text-align: left; font-size: .9rem; vertical-align: top; }}
  th {{ background: #f4f4f4; }}
  tr.conflict {{ background: #fff3f3; }}
  .conflict-block {{ background: #ffe4e4; border: 1px solid #e08a8a; padding: .6rem .8rem; margin: .5rem 0; border-radius: 4px; }}
</style>
</head>
<body>
<h1>inboxHero Dashboard</h1>

<h2>1. Pending Actions</h2>
<table>
<tr><th>Message</th><th>Proposed action</th><th>Why it needs a human</th><th>Status</th></tr>
{pending_rows}
</table>

<h2>2. Flagged</h2>
<table>
<tr><th>Message</th><th>Attempted</th><th>What the system did instead</th></tr>
{flagged_rows}
</table>

<h2>3. Commitments</h2>
{conflict_blocks}
<table>
<tr><th>Date</th><th>Time</th><th>Title</th><th>Source message ids</th><th>Detail</th></tr>
{commitment_rows}
</table>

</body>
</html>
"""


if __name__ == "__main__":
    html = render_html(build_dashboard())
    with open("dashboard.html", "w") as f:
        f.write(html)
    print("✓ Saved dashboard to dashboard.html")
