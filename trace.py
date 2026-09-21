"""
Unified capability trace log, written by demo.py and main.py.

One JSON line per event, tagged with the capability id that produced it (or
"FULL" for a whole-pipeline run via main.py), so a marker can verify a
specific capability's evidence (`cap=R2`, `cap=X1`, `cap=FULL`, ...) without
re-running anything. Kept at the repo root, alongside outbox/, since the
assignment names `trace.jsonl` as a top-level submission artifact.
"""

import json
import os
from datetime import datetime, timezone

TRACE_PATH = "trace.jsonl"


def trace_event(cap, event, data):
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "cap": cap, "event": event}
    entry.update(data)
    parent = os.path.dirname(TRACE_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(TRACE_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
