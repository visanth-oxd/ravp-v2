# Payment Failed Agent - Demo Guide

This guide shows you how to demo all capabilities of the Payment Failed Agent.

## Prerequisites

1. **Install dependencies:**
   ```bash
   cd agentic-factory-v1
   pip install -r requirements.txt
   ```

2. **Set Google API Key:**
   ```bash
   export GOOGLE_API_KEY=your_google_api_key_here
   ```

3. **Optional: Start Control-Plane** (for full factory features):
   ```bash
   # In a separate terminal
   cd agentic-factory-v1
   python -m uvicorn control_plane.api.main:app --port 8010
   ```

## Demo Method 1: Interactive CLI (Easiest)

### Start the CLI

```bash
cd agentic-factory-v1
python agents/payment_failed/cli.py
```

### Demo Commands

#### 1. Investigate a Payment Exception

```
agent> investigate EX-2025-001
```

**What happens:**
- Fetches exception data from PaymentProcessingSystem/TransactionEngine
- Fetches customer profile from CoreBankingSystem/CustomerDataSystem
- **LLM analyzes** the exception and suggests resolution
- Checks policy if retry is suggested
- Returns investigation results with LLM reasoning

**Expected output:**
```json
{
  "status": "success",
  "exception": {
    "exception_id": "EX-2025-001",
    "amount": 5000.0,
    "failure_reason": "insufficient_funds",
    ...
  },
  "customer": {
    "customer_id": "CUST-001",
    "tier": "standard",
    ...
  },
  "suggested_action": "retry",
  "confidence": 0.85,
  "evidence": [
    "Insufficient funds is temporary",
    "Customer has good payment history"
  ],
  "llm_reasoning": {
    "decision": "retry",
    "confidence": 0.85,
    "evidence": [...]
  },
  "policy_check": {
    "allowed": true,
    "reason": "Amount within limits, no previous retries"
  }
}
```

#### 2. Get Human-Readable Explanation

```
agent> explain EX-2025-001
```

**What happens:**
- Runs investigation first
- **LLM generates** human-readable explanation
- Returns formatted explanation text

**Expected output:**
```
Payment Exception EX-2025-001 failed due to insufficient funds. The customer's 
account had a balance of £3,000 but the payment required £5,000. 

Based on the customer's good payment history and the temporary nature of this 
issue, I recommend retrying the payment after verifying the account balance. 
The customer has a standard tier account with active status and verified KYC.

Suggested Action: retry
Confidence: 85%
Evidence:
- Insufficient funds is temporary
- Customer has good payment history  
- Amount is within policy limits
- No previous retry attempts

Note: Colleague must confirm this action in the system before it is executed.
```

#### 3. Execute Payment Retry (LLM-Driven)

```
agent> retry EX-2025-001
```

**What happens:**
- Automatically runs investigation
- **LLM decides** if retry is appropriate
- Checks policy if LLM suggests retry
- Executes retry if LLM suggests it AND policy allows
- Returns retry execution result

**Expected output:**
```json
{
  "status": "success",
  "exception_id": "EX-2025-001",
  "retry_id": "RETRY-20250204-143022",
  "message": "Payment retry initiated successfully. Retry ID: RETRY-20250204-143022",
  "retry_result": {
    "status": "success",
    "retry_id": "RETRY-20250204-143022",
    "exception_id": "EX-2025-001",
    "timestamp": "2025-02-04T14:30:22",
    ...
  }
}
```

#### 4. Force Retry (Skip Checks - Use with Caution)

```
agent> retry-force EX-2025-001
```

**What happens:**
- Skips investigation and policy checks
- Directly executes retry
- ⚠️ Use only for testing/demos

**Expected output:**
```json
{
  "status": "success",
  "exception_id": "EX-2025-001",
  "retry_id": "RETRY-20250204-143045",
  "message": "Payment retry initiated successfully. Retry ID: RETRY-20250204-143045"
}
```

## Demo Method 2: Python Script

Create a demo script:

```python
# demo_payment_agent.py
from agents.payment_failed.agent import PaymentFailedAgent

def demo_investigation():
    """Demo 1: Investigate payment exception"""
    print("\n" + "="*60)
    print("DEMO 1: Investigation with LLM Reasoning")
    print("="*60)
    
    agent = PaymentFailedAgent()
    result = agent.investigate_payment_exception("EX-2025-001")
    
    print(f"\nSuggested Action: {result['suggested_action']}")
    print(f"Confidence: {result['confidence']:.1%}")
    print(f"\nLLM Evidence:")
    for evidence in result['evidence']:
        print(f"  - {evidence}")
    
    if result.get('policy_check'):
        policy = result['policy_check']
        print(f"\nPolicy Check: {'✓ Allowed' if policy.get('allowed') else '✗ Denied'}")
        if not policy.get('allowed'):
            print(f"  Reason: {policy.get('reason')}")
    
    return result

def demo_explanation():
    """Demo 2: Get human-readable explanation"""
    print("\n" + "="*60)
    print("DEMO 2: Human-Readable Explanation")
    print("="*60)
    
    agent = PaymentFailedAgent()
    explanation = agent.explain_payment_failure("EX-2025-001")
    
    print(f"\n{explanation}")
    return explanation

def demo_retry():
    """Demo 3: Execute payment retry"""
    print("\n" + "="*60)
    print("DEMO 3: LLM-Driven Payment Retry")
    print("="*60)
    
    agent = PaymentFailedAgent()
    result = agent.retry_payment("EX-2025-001")
    
    print(f"\nRetry Status: {result['status']}")
    if result.get('retry_id'):
        print(f"Retry ID: {result['retry_id']}")
    print(f"Message: {result.get('message', 'N/A')}")
    
    if result['status'] == 'skipped':
        print(f"\nReason: {result.get('reason')}")
        print("\nInvestigation Result:")
        investigation = result.get('investigation', {})
        print(f"  Suggested Action: {investigation.get('suggested_action')}")
    
    return result

def demo_full_workflow():
    """Demo 4: Complete workflow"""
    print("\n" + "="*60)
    print("DEMO 4: Complete Workflow (Investigate → Explain → Retry)")
    print("="*60)
    
    agent = PaymentFailedAgent()
    exception_id = "EX-2025-001"
    
    # Step 1: Investigate
    print("\n[Step 1] Investigating exception...")
    investigation = agent.investigate_payment_exception(exception_id)
    print(f"✓ Investigation complete. Suggested: {investigation['suggested_action']}")
    
    # Step 2: Explain
    print("\n[Step 2] Generating explanation...")
    explanation = agent.explain_payment_failure(exception_id)
    print(f"✓ Explanation generated ({len(explanation)} characters)")
    
    # Step 3: Retry (if appropriate)
    print("\n[Step 3] Executing retry...")
    retry_result = agent.retry_payment(exception_id)
    
    if retry_result['status'] == 'success':
        print(f"✓ Retry executed successfully: {retry_result.get('retry_id')}")
    elif retry_result['status'] == 'denied':
        print(f"✗ Retry denied: {retry_result.get('reason')}")
    elif retry_result['status'] == 'skipped':
        print(f"⚠ Retry skipped: {retry_result.get('reason')}")
    
    return {
        "investigation": investigation,
        "explanation": explanation,
        "retry": retry_result
    }

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PAYMENT FAILED AGENT - DEMO")
    print("="*60)
    
    # Run all demos
    demo_investigation()
    demo_explanation()
    demo_retry()
    demo_full_workflow()
    
    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
```

Run it:

```bash
python demo_payment_agent.py
```

## Demo Method 3: One-Liner Commands

### Quick Investigation

```bash
python -c "from agents.payment_failed.agent import PaymentFailedAgent; agent = PaymentFailedAgent(); result = agent.investigate_payment_exception('EX-2025-001'); print(f\"Suggested: {result['suggested_action']}, Confidence: {result['confidence']:.1%}\")"
```

### Quick Explanation

```bash
python -c "from agents.payment_failed.agent import PaymentFailedAgent; agent = PaymentFailedAgent(); print(agent.explain_payment_failure('EX-2025-001'))"
```

### Quick Retry

```bash
python -c "from agents.payment_failed.agent import PaymentFailedAgent; agent = PaymentFailedAgent(); result = agent.retry_payment('EX-2025-001'); print(f\"Status: {result['status']}, Retry ID: {result.get('retry_id', 'N/A')}\")"
```

## Demo Scenarios

### Scenario 1: Successful Retry

**Exception:** EX-2025-001 (insufficient funds, good customer)
**Expected:** LLM suggests retry → Policy allows → Retry executed

```bash
agent> investigate EX-2025-001
# Should show: suggested_action: "retry", policy_check: {"allowed": true}

agent> retry EX-2025-001
# Should show: status: "success", retry_id: "RETRY-..."
```

### Scenario 2: Policy Denied Retry

**Exception:** EX-2025-002 (high amount, multiple retries)
**Expected:** LLM suggests retry → Policy denies → Retry skipped

```bash
agent> investigate EX-2025-002
# Should show: suggested_action: "retry", policy_check: {"allowed": false}

agent> retry EX-2025-002
# Should show: status: "denied", reason: "Policy check denied retry: ..."
```

### Scenario 3: LLM Suggests Escalation

**Exception:** EX-2025-003 (fraud risk, blocked account)
**Expected:** LLM suggests escalate → Retry skipped

```bash
agent> investigate EX-2025-003
# Should show: suggested_action: "escalate"

agent> retry EX-2025-003
# Should show: status: "skipped", reason: "Agent suggested action: escalate, not retry"
```

## What to Highlight in Demo

1. **LLM Reasoning** - Show how LLM analyzes exception and customer data
2. **Policy Governance** - Show how policies act as safety net
3. **Audit Trail** - Mention that all actions are logged (if control-plane running)
4. **Tool Integration** - Show how agent uses tools to fetch data
5. **Human-Readable Output** - Show explanation generation

## Troubleshooting

### Error: "LLM not available"
- Set `GOOGLE_API_KEY` environment variable
- Install `google-genai`: `pip install google-genai`

### Error: "Agent not found"
- Check that `config/agents/payment_failed.yaml` exists
- Verify you're running from `agentic-factory-v1` directory

### Error: "Module not found"
- Ensure you're in the `agentic-factory-v1` directory
- Check that `tools/` and `agent-sdk/` directories exist

## Next Steps

After demo, you can:
- Check audit logs (if control-plane running): `GET http://localhost:8010/audit/entries?agent_id=payment_failed`
- View agent definition: `GET http://localhost:8010/agents/payment_failed`
- Test with different exception IDs from `data/synthetic/payment_exceptions.json`
