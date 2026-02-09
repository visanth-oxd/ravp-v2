#!/usr/bin/env python3
"""
Test script for Policy Registry.
Run this to verify the policy registry is working.
"""

import sys
from pathlib import Path

# Add control-plane to path
repo_root = Path(__file__).resolve().parent.parent
control_plane = repo_root / "control-plane"
if str(control_plane) not in sys.path:
    sys.path.insert(0, str(control_plane))

from policy_registry.loader import evaluate, list_policies


def test_list_policies():
    """Test listing all policies."""
    print("=" * 60)
    print("Testing: List Policies")
    print("=" * 60)
    
    policies = list_policies()
    print(f"Found {len(policies)} policy/policies:")
    for policy in policies:
        print(f"  - {policy['id']}")
        print(f"    Path: {policy['path']}")
    print()


def test_evaluate_policy():
    """Test evaluating a policy."""
    print("=" * 60)
    print("Testing: Evaluate Policy")
    print("=" * 60)
    
    policy_id = "payments/retry"
    
    # Test case 1: Allowed (amount <= 10000, retries < 2)
    print("Test Case 1: Allowed (within limits)")
    input_data = {
        "amount": 5000,
        "previous_retries": 1,
        "beneficiary_blocked": False
    }
    result = evaluate(policy_id, input_data)
    print(f"  Input: {input_data}")
    print(f"  Result: {result}")
    print(f"  ✅ Allowed: {result['allowed']}")
    print()
    
    # Test case 2: Denied (amount > 10000)
    print("Test Case 2: Denied (amount too high)")
    input_data = {
        "amount": 15000,
        "previous_retries": 0,
        "beneficiary_blocked": False
    }
    result = evaluate(policy_id, input_data)
    print(f"  Input: {input_data}")
    print(f"  Result: {result}")
    print(f"  ❌ Allowed: {result['allowed']}")
    print()
    
    # Test case 3: Denied (too many retries)
    print("Test Case 3: Denied (too many retries)")
    input_data = {
        "amount": 5000,
        "previous_retries": 3,
        "beneficiary_blocked": False
    }
    result = evaluate(policy_id, input_data)
    print(f"  Input: {input_data}")
    print(f"  Result: {result}")
    print(f"  ❌ Allowed: {result['allowed']}")
    print()
    
    # Test case 4: Allowed (escalation requested)
    print("Test Case 4: Allowed (escalation requested)")
    input_data = {
        "amount": 15000,
        "previous_retries": 3,
        "escalation_requested": True,
        "beneficiary_blocked": False
    }
    result = evaluate(policy_id, input_data)
    print(f"  Input: {input_data}")
    print(f"  Result: {result}")
    print(f"  ✅ Allowed: {result['allowed']}")
    print()
    
    # Test case 5: Denied (beneficiary blocked)
    print("Test Case 5: Denied (beneficiary blocked)")
    input_data = {
        "amount": 5000,
        "previous_retries": 0,
        "beneficiary_blocked": True
    }
    result = evaluate(policy_id, input_data)
    print(f"  Input: {input_data}")
    print(f"  Result: {result}")
    print(f"  ❌ Allowed: {result['allowed']}")
    print()


if __name__ == "__main__":
    print("\n🧪 Testing Policy Registry\n")
    
    test_list_policies()
    test_evaluate_policy()
    
    print("=" * 60)
    print("✅ Tests complete!")
    print("=" * 60)
