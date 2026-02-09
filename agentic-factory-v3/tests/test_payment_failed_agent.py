#!/usr/bin/env python3
"""
Test script for Payment Failed Agent.
Run this to verify the agent is working.
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


def test_agent_initialization():
    """Test agent initialization."""
    print("=" * 60)
    print("Testing: Agent Initialization")
    print("=" * 60)
    
    from agents.payment_failed.agent import PaymentFailedAgent
    
    try:
        agent = PaymentFailedAgent()
        print(f"✅ Agent initialized successfully")
        print(f"  Agent ID: {agent.regulated.agent_id}")
        print(f"  Purpose: {agent.regulated.purpose}")
        print(f"  Risk Tier: {agent.regulated.risk_tier}")
        print(f"  Allowed Tools: {', '.join(agent.regulated.allowed_tools)}")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        raise
    print()


def test_investigate_exception():
    """Test investigating a payment exception."""
    print("=" * 60)
    print("Testing: Investigate Payment Exception")
    print("=" * 60)
    
    from agents.payment_failed.agent import PaymentFailedAgent
    
    agent = PaymentFailedAgent()
    
    # Test with valid exception ID
    print("\nTest Case 1: Valid exception ID")
    result = agent.investigate_payment_exception("EX-2025-001")
    print(f"  Input: EX-2025-001")
    print(f"  Status: {result['status']}")
    print(f"  Exception ID: {result['exception'].get('exception_id')}")
    print(f"  Failure Reason: {result['exception'].get('failure_reason')}")
    print(f"  Suggested Action: {result.get('suggested_action')}")
    assert result["status"] == "success", "Should succeed"
    assert result["exception"]["exception_id"] == "EX-2025-001", "Should match input"
    print("  ✅ Passed")
    
    # Test with invalid exception ID
    print("\nTest Case 2: Invalid exception ID")
    result = agent.investigate_payment_exception("EX-9999-999")
    print(f"  Input: EX-9999-999")
    print(f"  Status: {result['status']}")
    print(f"  Error: {result.get('error')}")
    assert result["status"] == "error", "Should return error"
    print("  ✅ Passed")
    print()


def test_explain_payment_failure():
    """Test explaining payment failure."""
    print("=" * 60)
    print("Testing: Explain Payment Failure")
    print("=" * 60)
    
    from agents.payment_failed.agent import PaymentFailedAgent
    
    agent = PaymentFailedAgent()
    
    explanation = agent.explain_payment_failure("EX-2025-001")
    print(f"\nExplanation:\n{explanation}")
    assert "EX-2025-001" in explanation, "Should include exception ID"
    assert "insufficient_funds" in explanation or "Failure Reason" in explanation, "Should include failure reason"
    print("\n  ✅ Passed")
    print()


if __name__ == "__main__":
    print("\n🧪 Testing Payment Failed Agent\n")
    
    test_agent_initialization()
    test_investigate_exception()
    test_explain_payment_failure()
    
    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
