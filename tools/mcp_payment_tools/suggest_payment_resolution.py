"""
MCP-style tool: suggest payment resolution (retry / waive_fee / escalate).

Advisory only; human must approve. Authority boundary for payment actions.
"""

import json


def suggest_payment_resolution(
    exception_id: str,
    suggested_action: str,
    reason: str,
) -> str:
    """
    Record suggested resolution. Advisory only; human must approve.
    
    Args:
        exception_id: Exception identifier (e.g. "EX-2025-001")
        suggested_action: Action to suggest ("retry" | "waive_fee" | "escalate")
        reason: Reason for the suggestion
    
    Returns:
        JSON string with confirmation message
    """
    return json.dumps({
        "status": "suggestion_recorded",
        "exception_id": exception_id,
        "suggested_action": suggested_action,
        "reason": reason,
        "human_approval_required": True,
        "message": "Colleague must confirm this action in the system before it is executed.",
    })
