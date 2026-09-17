import re

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "than", "so", "for",
    "to", "of", "in", "on", "at", "by", "with", "from", "is", "was", "are",
    "were", "be", "been", "being", "this", "that", "these", "those", "it",
    "its", "i", "you", "we", "they", "he", "she", "him", "her", "them",
    "will", "would", "can", "could", "should", "not", "no", "yes", "do",
    "does", "did", "have", "has", "had", "your", "our", "my", "as", "all",
    "re", "fwd",
}

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-]{2,}")


class Retriever:
    """
    Finds the earlier message(s) needed to ground a reply.

    Method 1 (primary): thread-walk -- pull every other message sharing the
    same thread_id. (e.g. t-api, t-launch).

    Method 2 (fallback): keyword-search -- if the thread alone has no answer
    (or the message has no thread), score every other message in the inbox
    by keyword overlap with the query message and return the best matches.
    """

    def __init__(self, inbox):
        self.inbox = inbox
        self.by_id = {m["id"]: m for m in inbox}

    def thread_walk(self, message):
        thread_id = message.get("thread_id")
        if not thread_id:
            return []
        others = [
            m for m in self.inbox
            if m.get("thread_id") == thread_id and m["id"] != message["id"]
        ]
        return sorted(others, key=lambda m: m.get("timestamp", ""))

    def keyword_search(self, message, min_overlap=2):
        query_terms = self._terms(message)
        if not query_terms:
            return []

        scored = []
        for m in self.inbox:
            if m["id"] == message["id"]:
                continue
            overlap = query_terms & self._terms(m)
            if len(overlap) >= min_overlap:
                scored.append((len(overlap), m))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [m for _, m in scored]

    def retrieve(self, message):
        """Thread-walk first; fall back to keyword-search only if the thread has nothing."""
        candidates = self.thread_walk(message)
        if candidates:
            return candidates, "thread-walk"

        candidates = self.keyword_search(message)
        if candidates:
            return candidates, "keyword-search"

        return [], "none"

    def verify_ids(self, ids):
        """Return any ids that do NOT exist in the mail store (should be empty)."""
        return [i for i in ids if i not in self.by_id]

    def _terms(self, message):
        text = f"{message.get('subject', '')} {message.get('body', '')}".lower()
        return {w for w in TOKEN_RE.findall(text) if w not in STOPWORDS}
