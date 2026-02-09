"""
MCP-style tool: flag suspicious account for review.
"""

import json
from datetime import datetime


def flag_suspicious_account(customer_id: str, reason: str, risk_score: float) -> str:
    """
    Flag a suspicious account for manual review.
    
    Args:
        customer_id: Customer identifier
        reason: Reason for flagging
        risk_score: Risk score (0.0 to 1.0)
    
    Returns:
        JSON string with flagging result
    """
    # Simulate flagging account
    # In production, this would call: POST /api/accounts/{customer_id}/flag
    
    flag_id = f"FLAG-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    return json.dumps({
        "status": "flagged",
        "flag_id": flag_id,
        "customer_id": customer_id,
        "reason": reason,
        "risk_score": risk_score,
        "timestamp": datetime.now().isoformat(),
        "requires_manual_review": True,
        "message": f"Account {customer_id} flagged for review. Flag ID: {flag_id}"
    })
