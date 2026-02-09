"""
Audit Store - Immutable log of all agent actions.

Provides:
- append(agent_id, event_type, payload) - Record an audit entry
- list_entries(agent_id, limit) - Query audit entries
- retention_days() - Get retention policy
"""

from .storage import append, list_entries, retention_days

__all__ = ["append", "list_entries", "retention_days"]
