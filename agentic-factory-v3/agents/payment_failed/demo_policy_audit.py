#!/usr/bin/env python3
"""
Demo script showing policy checks and audit logging.

Shows:
1. How policies are checked automatically
2. How audit logs are written
3. How to view audit logs
"""

import sys
import json
import time
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agents.payment_failed.agent import PaymentFailedAgent


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_policy_check():
    """Demo 1: Show policy check in action"""
    print_section("DEMO 1: Policy Check Flow")
    
    agent = PaymentFailedAgent()
    
    print("\nInvestigating exception EX-2025-001...")
    print("(Policy check happens automatically when LLM suggests 'retry')")
    print()
    
    result = agent.investigate_payment_exception("EX-2025-001")
    
    if result["status"] == "error":
        print(f"✗ Error: {result.get('error')}")
        return
    
    print("✓ Investigation Complete")
    print(f"\nLLM Suggested Action: {result['suggested_action']}")
    print(f"Confidence: {result['confidence']:.1%}")
    
    # Show policy check result
    policy_check = result.get('policy_check')
    if policy_check:
        print("\n" + "-" * 60)
        print("POLICY CHECK RESULT:")
        print("-" * 60)
        print(f"Policy ID: payments/retry")
        print(f"Allowed: {'✓ YES' if policy_check.get('allowed') else '✗ NO'}")
        print(f"Reason: {policy_check.get('reason', 'N/A')}")
        
        if policy_check.get('details'):
            print(f"\nDetails:")
            for key, value in policy_check['details'].items():
                print(f"  • {key}: {value}")
        
        # Show input data
        exception = result.get('exception', {})
        print(f"\nPolicy Input:")
        print(f"  • Amount: £{exception.get('amount', 0):,.2f}")
        print(f"  • Previous Retries: {exception.get('retry_count', 0)}")
        
        if not policy_check.get('allowed'):
            print(f"\n⚠ LLM suggested 'retry', but policy denied it.")
            print(f"  Action changed to: {result['suggested_action']}")
    else:
        print("\n⚠ No policy check performed (LLM suggested action other than 'retry')")
    
    return result


def demo_audit_logging():
    """Demo 2: Show audit logging"""
    print_section("DEMO 2: Audit Logging")
    
    print("\nRunning investigation...")
    print("(All actions are automatically logged to audit store)")
    print()
    
    agent = PaymentFailedAgent()
    result = agent.investigate_payment_exception("EX-2025-001")
    
    print("✓ Investigation complete")
    print("\n" + "-" * 60)
    print("AUDIT ENTRIES CREATED:")
    print("-" * 60)
    print("1. Tool Call: get_payment_exception")
    print("   - Args: {exception_id: 'EX-2025-001'}")
    print("   - Result summary: Exception data (first 200 chars)")
    print()
    print("2. Tool Call: get_customer_profile")
    print("   - Args: {customer_id: '...'}")
    print("   - Result summary: Customer data (first 200 chars)")
    print()
    
    if result.get('policy_check'):
        print("3. Policy Check: payments/retry")
        print("   - Input: {amount: ..., previous_retries: ...}")
        print(f"   - Result: {json.dumps(result['policy_check'], indent=2)}")
        print()
    
    print("4. Tool Call: suggest_payment_resolution")
    print(f"   - Args: {{suggested_action: '{result['suggested_action']}'}}")
    print("   - Result summary: Resolution suggestion")
    print()
    print("5. Decision: Investigation complete")
    print(f"   - Decision: 'Investigated exception EX-2025-001, LLM suggested {result['suggested_action']}'")
    print("   - Context: Full investigation result with LLM reasoning")
    
    return result


def demo_view_audit_logs():
    """Demo 3: View audit logs"""
    print_section("DEMO 3: Viewing Audit Logs")
    
    import requests
    
    control_plane_url = "http://localhost:8010"
    
    print(f"\nFetching audit logs from: {control_plane_url}")
    print()
    
    try:
        # Check if control-plane is available
        response = requests.get(f"{control_plane_url}/health", timeout=2)
        if response.status_code != 200:
            print("⚠ Control-plane not available. Start it with:")
            print("  python -m uvicorn control_plane.api.main:app --port 8010")
            return
        
        # Get audit entries
        response = requests.get(
            f"{control_plane_url}/audit/entries",
            params={"agent_id": "payment_failed", "limit": 5},
            timeout=5
        )
        
        if response.status_code == 200:
            entries = response.json()
            
            if entries:
                print(f"✓ Found {len(entries)} recent audit entries:")
                print()
                for i, entry in enumerate(entries, 1):
                    print(f"{i}. {entry['event_type'].upper()}")
                    print(f"   Timestamp: {entry.get('timestamp', 'N/A')}")
                    payload = entry.get('payload', {})
                    
                    if entry['event_type'] == 'tool_call':
                        print(f"   Tool: {payload.get('tool_name')}")
                        print(f"   Args: {json.dumps(payload.get('args', {}), indent=6)}")
                    
                    elif entry['event_type'] == 'policy_check':
                        print(f"   Policy: {payload.get('policy_id')}")
                        result = payload.get('result', {})
                        print(f"   Allowed: {result.get('allowed', 'N/A')}")
                        print(f"   Reason: {result.get('reason', 'N/A')}")
                    
                    elif entry['event_type'] == 'decision':
                        print(f"   Decision: {payload.get('decision', 'N/A')[:80]}...")
                    
                    print()
            else:
                print("⚠ No audit entries found.")
                print("  Run an investigation first to generate audit logs.")
        else:
            print(f"✗ Failed to fetch audit logs: {response.status_code}")
            print(f"  Response: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("⚠ Control-plane not available. Start it with:")
        print("  python -m uvicorn control_plane.api.main:app --port 8010")
    except Exception as e:
        print(f"✗ Error: {e}")


def demo_complete_flow():
    """Demo 4: Complete flow with policy and audit"""
    print_section("DEMO 4: Complete Flow (Policy + Audit)")
    
    agent = PaymentFailedAgent()
    exception_id = "EX-2025-001"
    
    print(f"\nExecuting retry for {exception_id}...")
    print("This will:")
    print("  1. Investigate (fetches data, LLM reasoning)")
    print("  2. Check policy (if LLM suggests retry)")
    print("  3. Log everything to audit")
    print("  4. Execute retry (if allowed)")
    print()
    
    time.sleep(1)
    
    result = agent.retry_payment(exception_id)
    
    print("✓ Process Complete")
    print("\n" + "-" * 60)
    print("SUMMARY:")
    print("-" * 60)
    print(f"Status: {result['status']}")
    
    if result.get('retry_id'):
        print(f"Retry ID: {result['retry_id']}")
    
    if result['status'] == 'success':
        print("\n✓ Retry executed successfully")
        print("  • Policy check: Passed")
        print("  • Audit logs: Created")
    elif result['status'] == 'denied':
        print("\n✗ Retry denied by policy")
        print(f"  • Reason: {result.get('reason')}")
        print("  • Audit logs: Created (policy denial logged)")
    elif result['status'] == 'skipped':
        print("\n⚠ Retry skipped")
        print(f"  • Reason: {result.get('reason')}")
        print("  • Audit logs: Created")
    
    print("\nTo view audit logs:")
    print("  curl http://localhost:8010/audit/entries?agent_id=payment_failed")
    
    return result


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("  POLICY CHECKS & AUDIT LOGGING - DEMO")
    print("=" * 60)
    print("\nThis demo shows:")
    print("  1. How policies are checked automatically")
    print("  2. How audit logs are written")
    print("  3. How to view audit logs")
    print("  4. Complete flow with policy and audit")
    
    # Check prerequisites
    import os
    if not os.environ.get("GOOGLE_API_KEY"):
        print("\n⚠ WARNING: GOOGLE_API_KEY not set. LLM features will not work.")
        response = input("\nContinue anyway? (y/n): ").strip().lower()
        if response != 'y':
            return 1
    
    # Run demos
    demo_policy_check()
    input("\nPress Enter to continue to next demo...")
    
    demo_audit_logging()
    input("\nPress Enter to continue to next demo...")
    
    demo_view_audit_logs()
    input("\nPress Enter to continue to final demo...")
    
    demo_complete_flow()
    
    # Summary
    print_section("DEMO SUMMARY")
    print("\nKey Takeaways:")
    print("  ✓ Policies are checked automatically when LLM suggests 'retry'")
    print("  ✓ Policy can override LLM decision (safety net)")
    print("  ✓ All tool calls are logged to audit")
    print("  ✓ All policy checks are logged to audit")
    print("  ✓ All decisions are logged to audit")
    print("  ✓ Audit logs are viewable via control-plane API")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(1)
