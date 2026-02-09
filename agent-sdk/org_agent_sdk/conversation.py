"""
Conversation buffer – bounded in-memory history for interactive agents.

Use this so the agent can keep track of the dialogue and pass recent turns
to the LLM for context (e.g. "the incident we discussed", "what you said earlier").
Every agent created from the template gets this; existing agents can add it too.
"""


class ConversationBuffer:
    """
    Bounded list of user/assistant messages for one interactive session.
    Call append_user() at the start of each turn, context_for_llm() when building
    the LLM prompt, and record_response() before returning a string to the user.
    """

    def __init__(self, max_messages: int = 20, max_content_len: int = 600):
        """
        Args:
            max_messages: Keep only the last N messages (trim from the front when over).
            max_content_len: Truncate each message to this many chars when formatting for LLM.
        """
        self._messages: list[dict[str, str]] = []
        self._max = max_messages
        self._max_content_len = max_content_len

    def append_user(self, content: str) -> None:
        """Record the current user message. Call at the start of answer()."""
        self._messages.append({"role": "user", "content": content})
        if len(self._messages) > self._max:
            self._messages = self._messages[-self._max:]

    def append_assistant(self, content: str) -> None:
        """Record the assistant response. Called by record_response()."""
        self._messages.append({"role": "assistant", "content": content})
        if len(self._messages) > self._max:
            self._messages = self._messages[-self._max:]

    def context_for_llm(self, exclude_last: int = 0) -> str:
        """
        Format recent messages for inclusion in the LLM prompt.
        Use exclude_last=1 so the "current" user message is not duplicated in context
        (you pass the current question separately).
        """
        messages = self._messages[:-exclude_last] if exclude_last else self._messages
        messages = messages[-self._max:]
        if not messages:
            return ""
        lines = []
        for m in messages:
            role = m.get("role", "")
            content = (m.get("content") or "")[: self._max_content_len].strip()
            if content:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def record_response(self, response: str | None) -> str | None:
        """
        Record the assistant response in history (if not None) and return the same.
        Use this before every string return in answer(): return self.conversation.record_response(msg).
        For quit (None), call: return None (do not call record_response).
        """
        if response is not None:
            self.append_assistant(response)
        return response
