"""
Unified capability trace log, written only by demo.py.

One JSON line per event, tagged with the capability id that produced it, so
a marker can verify a specific capability's evidence (`cap=R2`, `cap=X1`, ...)
without re-running the whole pipeline.
"""

import json
from datetime import datetime, timezone

TRACE_PATH = "trace.jsonl"


def trace_event(cap, event, data):
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "cap": cap, "event": event}
    entry.update(data)
    with open(TRACE_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
