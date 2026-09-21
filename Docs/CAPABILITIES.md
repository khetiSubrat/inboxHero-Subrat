# CAPABILITIES.md

**Student:** cert-aai-2026-06-0024
**Repository:** https://github.com/khetiSubrat/inboxHero-Subrat

Run one capability at a time -- this is what every `command` in
`capabilities.json` actually invokes:

```
python demo.py --cap R1              # one capability
python demo.py --cap R3 --dry-run    # propose sends without writing to outbox/
python demo.py --all --dry-run       # every capability, in manifest order
```

`demo.py` writes the same JSON artifacts a full run does (`model/dispositions.json`,
`model/draft.json`, `model/commitments.json`, ...) and appends a tagged event per
capability to `trace.jsonl`, so a marker can check one capability's evidence
in isolation. `main.py` is the full, undivided pipeline (`python main.py
--dry-run` / `python main.py`) that Parts 2-8 actually ship as; `demo.py`
re-exposes the same functions capability-by-capability for grading.

## The system, in one paragraph

A single Python pipeline, no framework. Messages are loaded once and pushed
through `classify_email()` -> `classify_to_disposition()`, a deterministic
rule cascade that resolves 80 of the 100 messages without a model and marks
the rest `REVIEW`. Before that, two other passes run over the raw inbox: a
standing-instruction learner (Part 5) and a hostile-instruction scanner
(Part 6), both independent of the classifier so a message can't dodge either
by also looking like a newsletter. `REPLY`-disposition messages go through
`ReplyAgent` (thread-walk/keyword retrieval, cited draft), then every send is
gated. A final pass extracts commitments, renders the dashboard, and runs
four extra capabilities (Part 8). State that must outlive a run (preferences,
sender trust) lives in `model/memory_store.json`; everything else is a plain JSON
file per part under `model/`.

## Design choices you were asked to state

- **Framework: none.** The pipeline is a fixed sequence with one branch per
  message (rule-path vs model-path for drafting), never a dynamic plan or
  multi-agent handoff. A graph/orchestration framework would add indirection
  without buying anything here -- see Final Report, Q1.
- **Retrieval: thread-walk, keyword-search fallback.** `thread_id` already
  encodes the structure a reply needs to be grounded in, so walking the
  thread is cheaper and more precise than embeddings for this dataset.
  Keyword overlap (`retriever.py`) only kicks in when a message has no
  thread-mates, e.g. cold-inbound messages like m042. See Final Report, Q2.
- **Reversible vs irreversible.** `send` and `delete` are irreversible
  (`gate.ACTION_MANIFEST`) and gated; `draft`, `archive`, `defer`, `label`
  run automatically. Delete is irreversible because the mock store has no
  trash, not because deleting is inherently unsafe.
- **Where the gate sits.** Exactly one function can write to `outbox/`
  (`outbox.send_message`), and it is only ever called from inside
  `ActionGate.run()` (`gate.py`). Email content is read as text by
  `ReplyAgent`/`guard_mail.py` but never executed as instructions -- there is
  no code path from "a message's body said X" to "the system did X". That is
  also the Part 6 defence: a hostile message can influence what gets
  *proposed*, never what gets sent.
- **Escalation line.** Only `send` and `delete` ever prompt; everything else
  (labelling a disposition, deferring, archiving) is automatic. See Final
  Report, Q3 for the trade-off this accepts.

## Capabilities

| id | name | tier | one-line claim |
|----|------|------|----------------|
| R1 | Zero the inbox | B | every message gets one disposition + reason, none left |
| R2 | Grounded reply | B | drafts cite the earlier message they used |
| R3 | Gate the irreversible | C | no send without approval or --dry-run |
| R4 | Persistent preference | C | two stated preferences each survive a restart |
| R5 | Refuse embedded instructions | C | detects, refuses, flags, reports 4 injection attempts |
| R6 | Dashboard | C | three panes, multi-message commitment, conflict surfaced |
| X1 | Daily digest | B | what happened / needs you / can wait, in one screen |
| X2 | Follow-up tracking | B | unanswered sent mail, with days-open |
| X3 | Unsubscribe advisor | B | recurring 100%-noise senders surfaced as a group |
| X4 | Persistent sender trust | B | BLOCK incidents accumulate across restarts, then escalate |

The exact command, observable outcome and evidence file for each is in
`capabilities.json` -- that is what a marking script reads; this file is for
a person. Keep the two in step.

## Final Report

**Q1 -- Why this framework?**
None, deliberately. The whole system is "load once, run a fixed sequence of
rule passes, branch once (model vs rule-based draft), gate the one
irreversible step." A LangChain/CrewAI-style framework earns its cost when
there's dynamic planning, tool selection, or multi-turn agent handoff; none
of that exists here, so a framework would only add a layer of indirection
between me and the one place (`gate.py`) that actually has to be trustworthy.

**Q2 -- Why this retrieval approach?**
The inbox already carries the structure a grounded reply needs: `thread_id`.
Walking the thread (`retriever.thread_walk`) is exact, cheap, and explainable
-- no embedding model, no similarity threshold to tune, and every candidate
is provably part of the same conversation. Keyword overlap
(`retriever.keyword_search`) is only the fallback for messages with no
thread-mates (cold inbound like m042, m016). I did not use embeddings because
this dataset's structure makes them unnecessary work for equivalent or worse
precision.

**Q3 -- Where did you draw the escalation line, and what did that trade away?**
Only `send` and `delete` ever ask for approval; `draft`, `archive`, `defer`,
and `label` run automatically, including the CC-on-legal-mail and
decline-and-counter-offer overrides from Part 5. The trade-off: a message
could be mis-archived or a meeting-time override could misfire, and the
owner won't be asked about it in the moment -- they'll only see it later in
`model/dispositions.json` or the dashboard. I accepted that in exchange for
not training the owner to reflexively click "yes" on dozens of routine,
reversible decisions per run, which would defeat the purpose of gating the
two actions that actually can't be undone.

**Q4 -- What did you trade away?**
Detection breadth for precision. `guard_mail.py`'s hostile-instruction
signals (`AGENT_ADDRESS_SIGNALS`/`ACTION_SIGNALS`) are a hand-written,
enumerable list, the same style as `classifier.py`'s rules -- so it will
catch the four injection patterns actually present in this inbox (m017,
m024, m039, m047) with no false positives, but it will miss a differently
worded injection that doesn't use any of those phrases. A semantic/LLM-based
detector would generalize further but would also (a) cost a model call per
message and (b) reintroduce exactly the risk Part 6 warns about: trusting a
model to reason correctly about text an attacker controls. I chose the
narrower, auditable rule set and accepted that it is not a complete defence
against every possible phrasing.
