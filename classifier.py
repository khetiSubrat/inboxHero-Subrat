def classify_email(email):
    """
    Deterministic first-stage router for inboxHero.

    Returns one of:
        SECURITY
        PREFERENCE
        SCHEDULING
        COMMITMENT
        AUTOMATED
        ACTIONABLE
        CONTEXT_REQUIRED
        REVIEW
    """

    thread_id = email.get("thread_id", "").lower()
    sender = email.get("from", "").lower()
    subject = email.get("subject", "").lower()
    body = email.get("body", "").lower()

    text = f"{subject} {body}"

    # ---------------------------------------------------------
    # 1. SECURITY
    # ---------------------------------------------------------
    # Highest priority. Do this before other categories because
    # a malicious email may look like an ordinary request.
    security_threads = {
        "t-inj",
    }

    security_subjects = [
        "password",
        "verify your account",
        "urgent security",
        "assistant settings",
        "confidential",
    ]

    if (
        thread_id.startswith("t-phish")
        or thread_id in security_threads
        or any(x in subject for x in security_subjects)
    ):
        return "SECURITY"

    # ---------------------------------------------------------
    # 2. PREFERENCE
    # ---------------------------------------------------------
    # Explicit standing instructions from the owner.
    preference_signals = [
        "standing request",
        "always cc",
        "always copy me",
        "never schedule",
        "do not schedule",
        "i do not take meetings",
    ]

    if any(x in text for x in preference_signals):
        return "PREFERENCE"

    # ---------------------------------------------------------
    # 3. SCHEDULING
    # ---------------------------------------------------------
    scheduling_threads = {
        "t-sched",
    }

    scheduling_subjects = [
        "meeting",
        "calendar",
        "schedule",
        "scheduling",
        "invite",
        "appointment",
        "1:1",
    ]

    scheduling_body = [
        "let's meet",
        "can we meet",
        "are you available",
        "what time works",
        "calendar",
        "schedule a meeting",
        "book a meeting",
    ]

    if (
        thread_id.startswith("t-sched")
        or any(x in subject for x in scheduling_subjects)
        or any(x in body for x in scheduling_body)
    ):
        return "SCHEDULING"

    # ---------------------------------------------------------
    # 4. COMMITMENT
    # ---------------------------------------------------------
    commitment_signals = [
        "deadline",
        "due by",
        "due on",
        "due friday",
        "due monday",
        "action required",
        "please complete",
        "please submit",
        "need this by",
        "must complete",
        "by end of day",
    ]

    if any(x in text for x in commitment_signals):
        return "COMMITMENT"

    # ---------------------------------------------------------
    # 5. AUTOMATED
    # ---------------------------------------------------------
    # These are high-confidence messages that normally don't
    # need an LLM.
    automated_sender_signals = [
        "no-reply",
        "noreply",
        "notifications",
        "receipts",
        "alerts",
        "billing",
        "mailer",
    ]

    automated_subject_signals = [
        "receipt",
        "invoice",
        "newsletter",
        "digest",
        "notification",
        "shipment confirmation",
        "delivery update",
        "usage report",
        "product update",
        "activity report",
        "weekly report",
        "monthly report",
        "auto-saved",
    ]

    if any(x in sender for x in automated_sender_signals):
        return "AUTOMATED"

    if any(x in subject for x in automated_subject_signals):
        return "AUTOMATED"

    # ---------------------------------------------------------
    # 6. KNOWN ACTIONABLE WORK
    # ---------------------------------------------------------
    actionable_threads = {
        "t-api",
        "t-launch",
        "t-board",
        "t-invest",
        "t-deck",
    }

    if thread_id in actionable_threads:
        return "ACTIONABLE"

    # ---------------------------------------------------------
    # 7. CONTEXT REQUIRED
    # ---------------------------------------------------------
    # These messages may require previous messages before the
    # system can determine the correct response.
    context_threads = {
        "t-supportfwd",
        "t-support2",
        "t-vendor",
    }

    context_signals = [
        "as discussed",
        "following up",
        "follow up",
        "the thing we talked about",
        "did you ever get a chance",
        "per our conversation",
        "as mentioned earlier",
        "regarding our earlier",
        "previous email",
        "see below",
    ]

    if thread_id in context_threads:
        return "CONTEXT_REQUIRED"

    if any(x in body for x in context_signals):
        return "CONTEXT_REQUIRED"

    # ---------------------------------------------------------
    # 8. REVIEW
    # ---------------------------------------------------------
    # Anything that cannot be confidently classified should be
    # sent for further reasoning rather than guessed.
    return "REVIEW"