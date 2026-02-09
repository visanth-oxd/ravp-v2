"""Audit store: in-memory with optional file append for demo. Retention = max in-memory entries."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# In-memory store (single process); for multi-instance use a real DB
_entries: list[dict[str, Any]] = []
_MAX_MEMORY = 10_000
_RETENTION_DAYS = 90  # for file retention policy doc


def _audit_file() -> Path | None:
    """
    Get audit file path from environment variable.
    
    Returns:
        Path to audit file, or None if AUDIT_FILE not set
    """
    if not os.environ.get("AUDIT_FILE"):
        return None
    return Path(os.environ["AUDIT_FILE"])


def append(agent_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Append an audit entry.
    
    Creates an immutable audit log entry with timestamp, agent_id, event_type,
    and payload. Stores in-memory and optionally appends to file.
    
    Args:
        agent_id: Agent identifier (e.g. "payment_failed")
        event_type: Type of event (e.g. "tool_call", "policy_check", "decision")
        payload: Event data (tool name, inputs, outputs, policy result, etc.)
    
    Returns:
        Created audit entry dict
    """
    entry = {
        "id": f"audit-{len(_entries)}-{datetime.now(timezone.utc).timestamp()}",
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "event_type": event_type,
        "payload": payload,
    }
    
    # Add to in-memory store
    _entries.append(entry)
    
    # Maintain max memory limit (FIFO)
    if len(_entries) > _MAX_MEMORY:
        _entries.pop(0)
    
    # Optionally append to file (for persistence)
    path = _audit_file()
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    
    return entry


def list_entries(agent_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """
    List audit entries, optionally filtered by agent_id.
    
    Args:
        agent_id: Optional filter by agent ID
        limit: Maximum number of entries to return (default: 100)
    
    Returns:
        List of audit entries (most recent first)
    """
    out = _entries
    
    # Filter by agent_id if provided
    if agent_id:
        out = [e for e in out if e.get("agent_id") == agent_id]
    
    # Return most recent entries (limit)
    return out[-limit:][::-1]


def retention_days() -> int:
    """
    Get audit retention policy in days.
    
    Returns:
        Number of days audit entries are retained
    """
    return _RETENTION_DAYS
