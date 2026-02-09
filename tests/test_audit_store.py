#!/usr/bin/env python3
"""
Test script for Audit Store.
Run this to verify the audit store is working.
"""

import sys
from pathlib import Path

# Add control-plane to path
repo_root = Path(__file__).resolve().parent.parent
control_plane = repo_root / "control-plane"
if str(control_plane) not in sys.path:
    sys.path.insert(0, str(control_plane))

from audit_store.storage import append, list_entries, retention_days


def test_append_entries():
    """Test appending audit entries."""
    print("=" * 60)
    print("Testing: Append Audit Entries")
    print("=" * 60)
    
    # Append tool call entry
    entry1 = append(
        agent_id="payment_failed",
        event_type="tool_call",
        payload={
            "tool": "get_payment_exception",
            "input": {"exception_id": "EX-2025-001"},
            "output": {"status": "found", "details": "..."}
        }
    )
    print(f"✅ Appended tool_call entry:")
    print(f"  ID: {entry1['id']}")
    print(f"  Agent: {entry1['agent_id']}")
    print(f"  Event: {entry1['event_type']}")
    print()
    
    # Append policy check entry
    entry2 = append(
        agent_id="payment_failed",
        event_type="policy_check",
        payload={
            "policy_id": "payments/retry",
            "input": {"amount": 5000, "previous_retries": 1},
            "result": {"allowed": True, "reason": "within_limits"}
        }
    )
    print(f"✅ Appended policy_check entry:")
    print(f"  ID: {entry2['id']}")
    print(f"  Policy: {entry2['payload']['policy_id']}")
    print(f"  Result: {entry2['payload']['result']['allowed']}")
    print()
    
    # Append decision entry
    entry3 = append(
        agent_id="payment_failed",
        event_type="decision",
        payload={
            "decision": "retry_payment",
            "confidence": 0.85,
            "reasoning": "Payment failed due to insufficient funds, retry recommended"
        }
    )
    print(f"✅ Appended decision entry:")
    print(f"  ID: {entry3['id']}")
    print(f"  Decision: {entry3['payload']['decision']}")
    print()


def test_list_entries():
    """Test listing audit entries."""
    print("=" * 60)
    print("Testing: List Audit Entries")
    print("=" * 60)
    
    # List all entries
    all_entries = list_entries(limit=10)
    print(f"Found {len(all_entries)} entry/entries (limit 10):")
    for entry in all_entries:
        print(f"  - [{entry['ts']}] {entry['agent_id']} - {entry['event_type']}")
    print()
    
    # List entries for specific agent
    agent_entries = list_entries(agent_id="payment_failed", limit=5)
    print(f"Found {len(agent_entries)} entry/entries for payment_failed:")
    for entry in agent_entries:
        print(f"  - [{entry['ts']}] {entry['event_type']}")
    print()


def test_retention():
    """Test retention policy."""
    print("=" * 60)
    print("Testing: Retention Policy")
    print("=" * 60)
    
    days = retention_days()
    print(f"Retention policy: {days} days")
    print()


if __name__ == "__main__":
    print("\n🧪 Testing Audit Store\n")
    
    test_append_entries()
    test_list_entries()
    test_retention()
    
    print("=" * 60)
    print("✅ Tests complete!")
    print("=" * 60)
