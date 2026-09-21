# inboxHero-Subrat
A sample Agentic AI POC.

## Reflection

**1. What did you refuse to automate?**
`m023` — the "quick favor -- confidential" email asking Sam to wire $3,200 to a vendor right now, from `priya.nair@paperjet.co` (not Priya's real `paperjet.io` address). The system blocks it and drafts nothing. I drew the line at anything that moves money or hinges on an identity claim I can't verify over email, because a keyword rule has no way to confirm who actually sent that message, and getting it wrong there isn't something you can walk back.

**2. Where does untrusted text enter your system?**
Every email body gets read as text to quote or pattern-match against, in `reply_agent.py` and `guard_mail.py` — never as something to execute. The only function that can cause an external effect, `send_message()` in `outbox.py`, is only ever called from inside `ActionGate.run()` in `gate.py`, and nothing in the classify/retrieve/draft path has a reference to it. So an attacker like `m024` (telling "automated assistants" to forward the mailbox) would have to get their own text to call that function directly — no wording defeats a gate that email content simply can't reach.

**3. Who is accountable when it sends the wrong thing?**
Sam is, since nothing reaches `outbox/` without him either approving the prompt in `gate.py` or reviewing a `--dry-run` first. If something goes out badly worded or to the wrong person, `logs/gate_log.jsonl` has the exact draft text, the message id, and the approval timestamp, and `draft.json` has what it was grounded in — so tracing a bad send back to either a bad retrieval or a rubber-stamped approval is a two-file lookup, not a guess.

**4. Name your own machinery.**
There's no framework, so I wrote the pieces by hand: the part-functions in `main.py` (`draft_replies`, `send_replies`, `scan_hostile_inbox`) are my Tasks, `classify_to_disposition()` in `disposition.py` is the router, `ActionGate` is the closest thing to a Crew since every irreversible task has to pass through it, and `ReplyAgent` is the one real Agent — the only thing that calls a model. The one thing I built myself that a framework hands you for free is the model-failure fallback (`ReplyAgent._compose()` catching an API error and dropping to rule-based quoting); a framework would've helped there, but I don't want one deciding when `gate.py` gets to fire — that path needs to stay narrow and mine.

