"""
MCP-style tool: get payment exception from PaymentProcessingSystem/TransactionEngine.

Authority boundary: only this module talks to exception data.

When PAYMENT_EXCEPTIONS_API_URL is set, calls the real API. Otherwise uses
synthetic data from data/synthetic/payment_exceptions.json (for demos).
"""

import json
import os
from pathlib import Path

import requests

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic"

# -----------------------------------------------------------------------------
# API configuration (use in production)
# -----------------------------------------------------------------------------
# PAYMENT_EXCEPTIONS_API_URL - base URL for the payment exceptions API
#   e.g. https://api.yourbank.com/payment-exceptions  or  https://apigee.example.com/v1/exceptions
#   The tool will call: GET {PAYMENT_EXCEPTIONS_API_URL}/{exception_id}
# PAYMENT_API_KEY or PAYMENT_API_HEADER - optional auth
#   If PAYMENT_API_KEY is set, sends X-Api-Key: {value}
#   If PAYMENT_API_HEADER is set, sends Authorization: {value}
# PAYMENT_API_TIMEOUT - request timeout in seconds (default 10)
# -----------------------------------------------------------------------------


def _fetch_from_api(exception_id: str) -> str:
    """
    Fetch payment exception from the configured API.
    Returns JSON string (same contract as synthetic) for success or error.
    """
    base_url = (os.environ.get("PAYMENT_EXCEPTIONS_API_URL") or "").rstrip("/")
    if not base_url:
        return json.dumps({"error": "PAYMENT_EXCEPTIONS_API_URL not configured", "exception_id": exception_id})

    timeout = int(os.environ.get("PAYMENT_API_TIMEOUT", "10"))
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    api_key = os.environ.get("PAYMENT_API_KEY")
    if api_key:
        headers["X-Api-Key"] = api_key
    auth_header = os.environ.get("PAYMENT_API_HEADER")
    if auth_header:
        headers["Authorization"] = auth_header

    url = f"{base_url}/{exception_id}"
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
    except requests.exceptions.Timeout:
        return json.dumps({
            "error": "API request timed out",
            "exception_id": exception_id,
        })
    except requests.exceptions.RequestException as e:
        return json.dumps({
            "error": f"API request failed: {e!s}",
            "exception_id": exception_id,
        })

    if response.status_code == 404:
        return json.dumps({
            "error": "Exception not found",
            "exception_id": exception_id,
        })
    if response.status_code >= 500:
        return json.dumps({
            "error": f"API error: {response.status_code}",
            "exception_id": exception_id,
        })
    if response.status_code != 200:
        return json.dumps({
            "error": f"API returned {response.status_code}",
            "exception_id": exception_id,
        })

    try:
        data = response.json()
    except ValueError:
        return json.dumps({
            "error": "Invalid JSON from API",
            "exception_id": exception_id,
        })

    # Normalise to expected shape if API uses different keys (e.g. id vs exception_id)
    if isinstance(data, dict) and "exception_id" not in data and "id" in data:
        data = dict(data)
        data["exception_id"] = data.get("id")
    return json.dumps(data, indent=2)


def _fetch_from_synthetic(exception_id: str) -> str:
    """Fetch from local synthetic data (demos)."""
    path = _DATA_DIR / "payment_exceptions.json"
    if not path.exists():
        return json.dumps({
            "error": "Data not found",
            "exception_id": exception_id,
        })
    with open(path, "r") as f:
        records = json.load(f)
    for record in records:
        if record.get("exception_id") == exception_id:
            return json.dumps(record, indent=2)
    return json.dumps({
        "error": "Exception not found",
        "exception_id": exception_id,
    })


def get_payment_exception(exception_id: str) -> str:
    """
    Fetch payment exception details from PaymentProcessingSystem/TransactionEngine.

    If PAYMENT_EXCEPTIONS_API_URL is set, calls:
        GET {PAYMENT_EXCEPTIONS_API_URL}/{exception_id}
    with optional auth (PAYMENT_API_KEY or PAYMENT_API_HEADER). Otherwise reads
    from data/synthetic/payment_exceptions.json.

    Args:
        exception_id: Exception identifier (e.g. "EX-2025-001")

    Returns:
        JSON string of exception record, or {"error": "...", "exception_id": "..."} if not found/failed
    """
    if os.environ.get("PAYMENT_EXCEPTIONS_API_URL"):
        return _fetch_from_api(exception_id)
    return _fetch_from_synthetic(exception_id)
