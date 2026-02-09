"""
API-based tool: get customer profile from public API (JSONPlaceholder example).

This is an example showing how to use public APIs instead of JSON files.
Set USE_API=true environment variable to enable.
"""

import json
import os
import requests
from pathlib import Path
from typing import Optional

# Configuration
USE_API = os.getenv("USE_API", "false").lower() == "true"
API_BASE_URL = os.getenv("CUSTOMER_API_URL", "https://jsonplaceholder.typicode.com")
API_KEY = os.getenv("CUSTOMER_API_KEY", "")  # Optional, not needed for JSONPlaceholder
TIMEOUT = int(os.getenv("API_TIMEOUT", "5"))

# File fallback path
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic"


def get_customer_profile(customer_id: str) -> str:
    """
    Fetch customer profile from API (if enabled) or file fallback.
    
    Args:
        customer_id: Customer identifier (e.g. "1" for JSONPlaceholder, "CUST-7001" for file)
    
    Returns:
        JSON string of customer record, or error message if not found
    """
    # Try API first if enabled
    if USE_API:
        try:
            headers = {"Content-Type": "application/json"}
            if API_KEY:
                headers["Authorization"] = f"Bearer {API_KEY}"
            
            # Call API
            response = requests.get(
                f"{API_BASE_URL}/users/{customer_id}",
                headers=headers,
                timeout=TIMEOUT
            )
            
            if response.status_code == 200:
                api_data = response.json()
                # Transform API response to our standard format
                return json.dumps(_transform_api_response(api_data), indent=2)
            elif response.status_code == 404:
                return json.dumps({
                    "error": "Customer not found in API",
                    "customer_id": customer_id
                })
            else:
                return json.dumps({
                    "error": f"API returned status {response.status_code}",
                    "customer_id": customer_id
                })
                
        except requests.exceptions.Timeout:
            print(f"API timeout for customer {customer_id}, falling back to file")
        except requests.exceptions.RequestException as e:
            print(f"API error for customer {customer_id}: {e}, falling back to file")
    
    # File fallback (existing implementation)
    return _get_from_file(customer_id)


def _transform_api_response(api_data: dict) -> dict:
    """
    Transform API response to our standard customer format.
    
    JSONPlaceholder format:
    {
        "id": 1,
        "name": "Leanne Graham",
        "email": "Sincere@april.biz",
        "phone": "1-770-736-8031 x56442",
        ...
    }
    
    Our format:
    {
        "customer_id": "1",
        "name": "Leanne Graham",
        "email": "Sincere@april.biz",
        "phone": "1-770-736-8031 x56442",
        "balance": 0.0,
        "tier": "standard",
        "status": "active",
        ...
    }
    """
    return {
        "customer_id": str(api_data.get("id", "")),
        "name": api_data.get("name", ""),
        "email": api_data.get("email", ""),
        "phone": api_data.get("phone", ""),
        "account_number": "",  # Not available in JSONPlaceholder
        "account_type": "current",
        "balance": 0.0,  # Not available in JSONPlaceholder
        "currency": "GBP",
        "tier": "standard",
        "status": "active",
        "kyc_status": "verified",
        "risk_level": "low"
    }


def _get_from_file(customer_id: str) -> str:
    """Fallback: read from JSON file (original implementation)."""
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


# Example usage:
# export USE_API=true
# export CUSTOMER_API_URL=https://jsonplaceholder.typicode.com
# python -c "from tools.mcp_customer_tools.get_customer_profile_api import get_customer_profile; print(get_customer_profile('1'))"
