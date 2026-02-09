"""
MCP-style tool: check risk score for customer/transaction.
"""

import json


def check_risk_score(customer_id: str, transaction_id: str | None = None) -> str:
    """
    Check risk score for customer or specific transaction.
    
    In production, this would call:
    - RiskManagementSystem API: GET /risk/score?customer_id={customer_id}&transaction_id={transaction_id}
    
    Args:
        customer_id: Customer identifier
        transaction_id: Optional transaction identifier
    
    Returns:
        JSON string with risk score and details
    """
    # Simulate risk scoring
    # In production, this would call: GET /api/risk/score?customer_id=...&transaction_id=...
    
    # Calculate risk score based on various factors
    base_score = 0.3
    
    # Add risk factors
    risk_factors = []
    
    # Multiple failed transactions increase risk
    if transaction_id and "failed" in transaction_id.lower():
        base_score += 0.3
        risk_factors.append("Multiple failed transactions")
    
    # High-value transactions increase risk
    if transaction_id:
        base_score += 0.2
        risk_factors.append("High-value transaction")
    
    # Location changes increase risk
    base_score += 0.2
    risk_factors.append("Rapid location changes")
    
    # Cap at 1.0
    risk_score = min(base_score, 1.0)
    
    # Determine risk tier
    if risk_score >= 0.8:
        risk_tier = "high"
    elif risk_score >= 0.5:
        risk_tier = "medium"
    else:
        risk_tier = "low"
    
    return json.dumps({
        "customer_id": customer_id,
        "transaction_id": transaction_id,
        "risk_score": round(risk_score, 2),
        "risk_tier": risk_tier,
        "risk_factors": risk_factors,
        "recommendation": "block" if risk_score >= 0.8 else "flag" if risk_score >= 0.5 else "monitor"
    })
