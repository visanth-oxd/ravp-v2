"""
MCP-style tool: get customer profile from CoreBankingSystem/CustomerDataSystem.

Authority boundary: only this module talks to customer data.
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic"


def get_customer_profile(customer_id: str) -> str:
    """
    Fetch customer profile from CoreBankingSystem/CustomerDataSystem.
    
    In production, this would call:
    - CoreBankingSystem API: GET /customers/{customer_id}
    - CustomerDataSystem API: GET /profiles/{customer_id}
    
    Args:
        customer_id: Customer identifier (e.g. "CUST-7001")
    
    Returns:
        JSON string of customer record, or error message if not found
    """
    path = _DATA_DIR / "customers.json"
    
    if not path.exists():
        return json.dumps({
            "error": "Data not found",
            "customer_id": customer_id
        })
    
    with open(path, "r") as f:
        records = json.load(f)
    
    for record in records:
        if record.get("customer_id") == customer_id:
            return json.dumps(record, indent=2)
    
    return json.dumps({
        "error": "Customer not found",
        "customer_id": customer_id
    })
