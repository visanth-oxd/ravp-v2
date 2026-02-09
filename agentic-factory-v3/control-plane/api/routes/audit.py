"""Audit Store API – append and query audit entries."""

import sys
from pathlib import Path

from fastapi import APIRouter

# Add control-plane to path for imports
control_plane_dir = Path(__file__).resolve().parent.parent.parent
if str(control_plane_dir) not in sys.path:
    sys.path.insert(0, str(control_plane_dir))

from audit_store.storage import append, list_entries, retention_days

router = APIRouter(prefix="/audit", tags=["audit-store"])


@router.post("/entries")
def append_audit_api(body: dict):
    """
    Append an audit entry.
    
    Body should contain:
    - agent_id: Agent identifier
    - event_type: Type of event (tool_call, policy_check, decision, etc.)
    - payload: Event data
    
    Returns:
        Created audit entry
    """
    agent_id = body.get("agent_id", "")
    event_type = body.get("event_type", "tool_call")
    payload = body.get("payload", body)
    
    entry = append(agent_id, event_type, payload)
    return entry


@router.get("/entries")
def list_audit_api(agent_id: str | None = None, limit: int = 100):
    """
    List audit entries.
    
    Args:
        agent_id: Optional filter by agent ID
        limit: Maximum number of entries to return (default: 100)
    
    Returns:
        {"entries": [...], "retention_days": 90}
    """
    return {
        "entries": list_entries(agent_id=agent_id, limit=limit),
        "retention_days": retention_days()
    }
