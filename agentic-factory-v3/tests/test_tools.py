#!/usr/bin/env python3
"""
Test script for Tools.
Run this to verify the tools are working.
"""

import sys
import json
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def test_get_payment_exception():
    """Test get_payment_exception tool."""
    print("=" * 60)
    print("Testing: get_payment_exception")
    print("=" * 60)
    
    from tools.mcp_payment_tools import get_payment_exception
    
    # Test case 1: Valid exception ID
    print("\nTest Case 1: Valid exception ID")
    result = get_payment_exception("EX-2025-001")
    data = json.loads(result)
    print(f"  Input: EX-2025-001")
    print(f"  Result: {json.dumps(data, indent=2)}")
    assert "exception_id" in data, "Should return exception data"
    assert data["exception_id"] == "EX-2025-001", "Should match input"
    print("  ✅ Passed")
    
    # Test case 2: Invalid exception ID
    print("\nTest Case 2: Invalid exception ID")
    result = get_payment_exception("EX-9999-999")
    data = json.loads(result)
    print(f"  Input: EX-9999-999")
    print(f"  Result: {json.dumps(data, indent=2)}")
    assert "error" in data, "Should return error"
    assert data["error"] == "Exception not found", "Should indicate not found"
    print("  ✅ Passed")
    print()


def test_suggest_payment_resolution():
    """Test suggest_payment_resolution tool."""
    print("=" * 60)
    print("Testing: suggest_payment_resolution")
    print("=" * 60)
    
    from tools.mcp_payment_tools import suggest_payment_resolution
    
    # Test case 1: Suggest retry
    print("\nTest Case 1: Suggest retry")
    result = suggest_payment_resolution(
        exception_id="EX-2025-001",
        suggested_action="retry",
        reason="Insufficient funds, retry after balance check"
    )
    data = json.loads(result)
    print(f"  Input: exception_id=EX-2025-001, action=retry")
    print(f"  Result: {json.dumps(data, indent=2)}")
    assert data["status"] == "suggestion_recorded", "Should record suggestion"
    assert data["suggested_action"] == "retry", "Should match input"
    assert data["human_approval_required"] == True, "Should require approval"
    print("  ✅ Passed")
    
    # Test case 2: Suggest escalate
    print("\nTest Case 2: Suggest escalate")
    result = suggest_payment_resolution(
        exception_id="EX-2025-002",
        suggested_action="escalate",
        reason="Account frozen, requires manual review"
    )
    data = json.loads(result)
    print(f"  Input: exception_id=EX-2025-002, action=escalate")
    print(f"  Result: {json.dumps(data, indent=2)}")
    assert data["suggested_action"] == "escalate", "Should match input"
    print("  ✅ Passed")
    print()


def test_get_customer_profile():
    """Test get_customer_profile tool."""
    print("=" * 60)
    print("Testing: get_customer_profile")
    print("=" * 60)
    
    from tools.mcp_customer_tools import get_customer_profile
    
    # Test case 1: Valid customer ID
    print("\nTest Case 1: Valid customer ID")
    result = get_customer_profile("CUST-7001")
    data = json.loads(result)
    print(f"  Input: CUST-7001")
    print(f"  Result: {json.dumps(data, indent=2)}")
    assert "customer_id" in data, "Should return customer data"
    assert data["customer_id"] == "CUST-7001", "Should match input"
    assert "name" in data, "Should include customer name"
    print("  ✅ Passed")
    
    # Test case 2: Invalid customer ID
    print("\nTest Case 2: Invalid customer ID")
    result = get_customer_profile("CUST-9999")
    data = json.loads(result)
    print(f"  Input: CUST-9999")
    print(f"  Result: {json.dumps(data, indent=2)}")
    assert "error" in data, "Should return error"
    assert data["error"] == "Customer not found", "Should indicate not found"
    print("  ✅ Passed")
    print()


def test_tool_imports():
    """Test that tools can be imported correctly."""
    print("=" * 60)
    print("Testing: Tool Imports")
    print("=" * 60)
    
    try:
        from tools.mcp_payment_tools import get_payment_exception, suggest_payment_resolution
        print("  ✅ Payment tools imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import payment tools: {e}")
        raise
    
    try:
        from tools.mcp_customer_tools import get_customer_profile
        print("  ✅ Customer tools imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import customer tools: {e}")
        raise
    
    print()


if __name__ == "__main__":
    print("\n🧪 Testing Tools\n")
    
    test_tool_imports()
    test_get_payment_exception()
    test_suggest_payment_resolution()
    test_get_customer_profile()
    
    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
