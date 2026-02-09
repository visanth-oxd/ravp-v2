#!/usr/bin/env python3
"""
Demo script for Payment Failed Agent capabilities.

Shows all three main capabilities:
1. Investigation with LLM reasoning
2. Human-readable explanation
3. LLM-driven payment retry
"""

import sys
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


def demo_investigation():
    """Demo 1: Investigate payment exception"""
    print_section("DEMO 1: Investigation with LLM Reasoning")
    
    try:
        agent = PaymentFailedAgent()
        print("\nInvestigating exception EX-2025-001...")
        result = agent.investigate_payment_exception("EX-2025-001")
        
        if result["status"] == "error":
            print(f"✗ Error: {result.get('error')}")
            return result
        
        print("\n✓ Investigation Complete")
        print(f"\nSuggested Action: {result['suggested_action']}")
        print(f"Confidence: {result['confidence']:.1%}")
        
        print(f"\nLLM Evidence:")
        for evidence in result.get('evidence', [])[:5]:  # Show first 5
            print(f"  • {evidence}")
        
        if result.get('policy_check'):
            policy = result['policy_check']
            status = "✓ Allowed" if policy.get('allowed') else "✗ Denied"
            print(f"\nPolicy Check: {status}")
            if not policy.get('allowed'):
                print(f"  Reason: {policy.get('reason', 'N/A')}")
        
        print(f"\nException Details:")
        exception = result.get('exception', {})
        print(f"  • ID: {exception.get('exception_id')}")
        print(f"  • Amount: £{exception.get('amount', 0):,.2f}")
        print(f"  • Failure Reason: {exception.get('failure_reason', 'N/A')}")
        
        return result
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_explanation():
    """Demo 2: Get human-readable explanation"""
    print_section("DEMO 2: Human-Readable Explanation")
    
    try:
        agent = PaymentFailedAgent()
        print("\nGenerating explanation for EX-2025-001...")
        explanation = agent.explain_payment_failure("EX-2025-001")
        
        print("\n✓ Explanation Generated")
        print("\n" + "-" * 60)
        print(explanation)
        print("-" * 60)
        
        return explanation
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_retry():
    """Demo 3: Execute payment retry"""
    print_section("DEMO 3: LLM-Driven Payment Retry")
    
    try:
        agent = PaymentFailedAgent()
        print("\nExecuting retry for EX-2025-001...")
        print("(This will investigate first, then execute retry if LLM suggests it)")
        
        result = agent.retry_payment("EX-2025-001")
        
        print("\n✓ Retry Process Complete")
        print(f"\nStatus: {result['status']}")
        
        if result.get('retry_id'):
            print(f"Retry ID: {result['retry_id']}")
        
        if result.get('message'):
            print(f"Message: {result['message']}")
        
        if result['status'] == 'skipped':
            print(f"\n⚠ Retry Skipped")
            print(f"Reason: {result.get('reason')}")
            investigation = result.get('investigation', {})
            if investigation:
                print(f"\nInvestigation showed:")
                print(f"  • Suggested Action: {investigation.get('suggested_action')}")
                print(f"  • Confidence: {investigation.get('confidence', 0):.1%}")
        
        elif result['status'] == 'denied':
            print(f"\n✗ Retry Denied")
            print(f"Reason: {result.get('reason')}")
        
        elif result['status'] == 'success':
            print(f"\n✓ Retry Executed Successfully")
            retry_result = result.get('retry_result', {})
            if retry_result:
                print(f"  • Retry ID: {retry_result.get('retry_id')}")
                print(f"  • Timestamp: {retry_result.get('timestamp')}")
        
        return result
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_full_workflow():
    """Demo 4: Complete workflow"""
    print_section("DEMO 4: Complete Workflow (Investigate → Explain → Retry)")
    
    try:
        agent = PaymentFailedAgent()
        exception_id = "EX-2025-001"
        
        # Step 1: Investigate
        print("\n[Step 1/3] Investigating exception...")
        investigation = agent.investigate_payment_exception(exception_id)
        if investigation["status"] == "error":
            print(f"✗ Investigation failed: {investigation.get('error')}")
            return None
        print(f"✓ Investigation complete")
        print(f"  • Suggested Action: {investigation['suggested_action']}")
        print(f"  • Confidence: {investigation['confidence']:.1%}")
        
        # Step 2: Explain
        print("\n[Step 2/3] Generating explanation...")
        explanation = agent.explain_payment_failure(exception_id)
        print(f"✓ Explanation generated ({len(explanation)} characters)")
        print(f"  Preview: {explanation[:100]}...")
        
        # Step 3: Retry (if appropriate)
        print("\n[Step 3/3] Executing retry...")
        retry_result = agent.retry_payment(exception_id)
        
        if retry_result['status'] == 'success':
            print(f"✓ Retry executed successfully")
            print(f"  • Retry ID: {retry_result.get('retry_id')}")
        elif retry_result['status'] == 'denied':
            print(f"✗ Retry denied by policy")
            print(f"  • Reason: {retry_result.get('reason')}")
        elif retry_result['status'] == 'skipped':
            print(f"⚠ Retry skipped")
            print(f"  • Reason: {retry_result.get('reason')}")
        else:
            print(f"✗ Retry failed: {retry_result.get('status')}")
        
        return {
            "investigation": investigation,
            "explanation": explanation,
            "retry": retry_result
        }
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("  PAYMENT FAILED AGENT - DEMO")
    print("=" * 60)
    print("\nThis demo shows:")
    print("  1. Investigation with LLM reasoning")
    print("  2. Human-readable explanation generation")
    print("  3. LLM-driven payment retry execution")
    print("  4. Complete workflow")
    
    # Check prerequisites
    import os
    if not os.environ.get("GOOGLE_API_KEY"):
        print("\n⚠ WARNING: GOOGLE_API_KEY not set. LLM features will not work.")
        print("Set it with: export GOOGLE_API_KEY=your_key")
        response = input("\nContinue anyway? (y/n): ").strip().lower()
        if response != 'y':
            return 1
    
    # Run demos
    results = {}
    
    results['investigation'] = demo_investigation()
    input("\nPress Enter to continue to next demo...")
    
    results['explanation'] = demo_explanation()
    input("\nPress Enter to continue to next demo...")
    
    results['retry'] = demo_retry()
    input("\nPress Enter to continue to final demo...")
    
    results['workflow'] = demo_full_workflow()
    
    # Summary
    print_section("DEMO SUMMARY")
    print("\nAll demos completed!")
    print("\nKey Takeaways:")
    print("  ✓ Agent uses LLM to analyze payment exceptions")
    print("  ✓ LLM decides whether to retry, escalate, or waive fee")
    print("  ✓ Policies act as governance layer (safety net)")
    print("  ✓ All actions are audited")
    print("  ✓ Human-readable explanations generated automatically")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(1)
