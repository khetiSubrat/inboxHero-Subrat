from retriever import Retriever
from model_agent import ModelAgent

RETRIEVAL_MANIFEST = "thread-walk+keyword-search"


class ReplyAgent(ModelAgent):
    """
    Part 3: Answering Properly.

    Drafts a reply only when it can ground it in a real earlier message,
    citing the message ids it used. Refuses to draft (returns grounded=False)
    when the inbox has nothing to ground the answer in.
    """

    def __init__(self, inbox):
        self.retriever = Retriever(inbox)
        self.model = self._load_model()  # model/key come from config, not from init args

    def draft_reply(self, message_id):
        message = self.retriever.by_id.get(message_id)
        if message is None:
            raise ValueError(f"Unknown message id: {message_id}")

        candidates, method = self.retriever.retrieve(message)
        if not candidates:
            return {
                "message_id": message_id,
                "draft": None,
                "source_message_ids": [],
                "retrieval_method": method,
                "grounded": False,
                "reason": "Not in inbox: no earlier message supports an answer.",
            }

        draft_text, source_message_ids = self._compose(message, candidates)

        # Every cited id must actually exist in the mail store -- never trust blindly.
        missing = self.retriever.verify_ids(source_message_ids)
        if missing:
            raise ValueError(f"Draft cited unknown message ids: {missing}")

        return {
            "message_id": message_id,
            "draft": draft_text,
            "source_message_ids": source_message_ids,
            "retrieval_method": method,
            "grounded": True,
        }

    def _compose(self, message, candidates):
        if self.model is not None:
            try:
                return self._compose_with_model(message, candidates)
            except Exception as e:
                print(f"⚠ Model draft failed for {message['id']} ({e}); falling back to rule-based draft.")
        return self._compose_rule_based(message, candidates)

    def _compose_with_model(self, message, candidates):
        context = "\n\n".join(
            f"[{c['id']}] from {c.get('from')} @ {c.get('timestamp')}\n"
            f"subject: {c.get('subject')}\nbody: {c.get('body')}"
            for c in candidates
        )
        prompt = (
            "You are drafting a reply to the message below. Use ONLY facts found "
            "in the earlier messages provided as context. Do not invent details. "
            "After the draft, add a line 'CITED: <comma separated message ids actually used>'.\n\n"
            f"Message to answer [{message['id']}]:\nsubject: {message.get('subject')}\n"
            f"body: {message.get('body')}\n\n"
            f"Earlier messages:\n{context}"
        )
        print(f"    querying model ({getattr(self.model, 'choose_model', '?')})...", flush=True)
        response = self.model._chat([{"role": "user", "content": prompt}])
        text = response.get("message", {}).get("content", "")
        draft, cited = self._split_cited(text)
        # Only trust ids that were actually offered as candidates.
        candidate_ids = {c["id"] for c in candidates}
        source_message_ids = [i for i in cited if i in candidate_ids]
        return draft, source_message_ids

    def _split_cited(self, text):
        marker = "CITED:"
        if marker not in text:
            return text.strip(), []
        draft, _, tail = text.partition(marker)
        cited = [c.strip() for c in tail.strip().split(",") if c.strip()]
        return draft.strip(), cited

    def _compose_rule_based(self, message, candidates):
        """No model available: quote the grounding message(s) directly, no invention."""
        top = candidates[0]
        draft = (
            f"Re: {message.get('subject', '')}\n\n"
            f"Following up on this -- from {top.get('from')} ({top['id']}): "
            f"\"{top.get('body', '').strip()}\""
        )
        return draft, [top["id"]]
