"""
MCP-style tool: get transaction history for fraud analysis.
"""

import json
from pathlib import Path

# Load synthetic transaction data
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic"


def get_transaction_history(customer_id: str, days: int = 30) -> str:
    """
    Get transaction history for a customer (for fraud analysis).
    
    In production, this would call:
    - PaymentProcessingSystem API: GET /transactions?customer_id={customer_id}&days={days}
    - TransactionEngine API: GET /history/{customer_id}?period={days}
    
    Args:
        customer_id: Customer identifier
        days: Number of days of history to retrieve
    
    Returns:
        JSON string with transaction history
    """
    # Simulate fetching transaction history
    # In production, this would call: GET /api/transactions?customer_id=...&days=...
    
    # For demo, return synthetic data
    transactions = [
        {
            "transaction_id": f"TXN-{customer_id}-001",
            "date": "2025-01-15",
            "amount": 1500.0,
            "status": "completed",
            "merchant": "Merchant A",
            "location": "London, UK"
        },
        {
            "transaction_id": f"TXN-{customer_id}-002",
            "date": "2025-01-20",
            "amount": 2500.0,
            "status": "completed",
            "merchant": "Merchant B",
            "location": "London, UK"
        },
        {
            "transaction_id": f"TXN-{customer_id}-003",
            "date": "2025-02-01",
            "amount": 5000.0,
            "status": "failed",
            "merchant": "Merchant C",
            "location": "New York, USA"  # Different location
        },
        {
            "transaction_id": f"TXN-{customer_id}-004",
            "date": "2025-02-02",
            "amount": 10000.0,
            "status": "failed",
            "merchant": "Merchant D",
            "location": "Tokyo, Japan"  # Very different location
        }
    ]
    
    return json.dumps({
        "customer_id": customer_id,
        "days": days,
        "transaction_count": len(transactions),
        "transactions": transactions,
        "risk_indicators": {
            "multiple_failed_transactions": True,
            "rapid_location_changes": True,
            "increasing_amounts": True
        }
    })
