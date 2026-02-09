"""
MCP-style tool: execute payment retry.

Executes a payment retry after policy checks and human approval (if required).
Authority boundary for payment actions.
"""

import json
from datetime import datetime


def execute_payment_retry(
    exception_id: str,
    amount: float | None = None,
    reason: str | None = None,
) -> str:
    """
    Execute a payment retry for a failed payment exception.
    
    This simulates calling the actual payment system (PaymentProcessingSystem/TransactionEngine) to retry the payment.
    In production, this would make an API call to the payment processing system:
    - PaymentProcessingSystem API: POST /payments/{exception_id}/retry
    - TransactionEngine API: POST /transactions/{exception_id}/retry
    
    Args:
        exception_id: Exception identifier (e.g. "EX-2025-001")
        amount: Optional amount to retry (if different from original)
        reason: Optional reason for the retry
    
    Returns:
        JSON string with retry execution result
    """
    # Simulate retry execution
    # In production, this would call: POST /api/payments/{exception_id}/retry
    
    retry_id = f"RETRY-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Simulate success/failure (in production, this would be the actual API response)
    # For demo purposes, assume 90% success rate
    import random
    success = random.random() > 0.1
    
    if success:
        return json.dumps({
            "status": "success",
            "retry_id": retry_id,
            "exception_id": exception_id,
            "message": f"Payment retry initiated successfully. Retry ID: {retry_id}",
            "timestamp": datetime.now().isoformat(),
            "amount": amount,
            "reason": reason or "Agent-initiated retry after investigation"
        })
    else:
        return json.dumps({
            "status": "failed",
            "retry_id": retry_id,
            "exception_id": exception_id,
            "error": "Payment retry failed - insufficient funds or account issue",
            "timestamp": datetime.now().isoformat(),
            "amount": amount,
            "reason": reason
        })
