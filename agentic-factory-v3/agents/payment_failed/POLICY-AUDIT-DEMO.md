# Policy Checks & Audit Logging - How It Works

This document shows exactly how the Payment Failed Agent checks policies and writes to audit logs.

## Policy Checking Flow

### 1. When Policy Check Happens

Policy checks occur **automatically** when:
- LLM suggests "retry" action during investigation
- Agent executes `retry_payment()` method

### 2. Policy Check Code (in `investigate_payment_exception`)

```python
# Step 4: Check policy if retry is suggested (governance)
policy_result = None
if suggested_action == "retry":
    try:
        # Call PolicyClient to evaluate policy
        policy_result = self.regulated.policy.evaluate("payments/retry", {
            "amount": exception_data.get("amount", 0),
            "previous_retries": exception_data.get("retry_count", 0),
            "beneficiary_blocked": False
        })
        
        # If policy denies retry, override LLM decision
        if not policy_result.get("allowed"):
            suggested_action = "escalate"
            evidence.append(f"Policy check denied retry: {policy_result.get('reason', 'N/A')}")
    except Exception as e:
        # Policy check failed, default to escalate
        suggested_action = "escalate"
        policy_result = {"allowed": False, "reason": str(e)}
        evidence.append(f"Policy check failed: {str(e)}")
    
    # Log policy check to audit
    self.regulated.audit.log_policy_check(
        agent_id=self.regulated.agent_id,
        policy_id="payments/retry",
        input_data={
            "amount": exception_data.get("amount", 0),
            "previous_retries": exception_data.get("retry_count", 0)
        },
        result=policy_result or {}
    )
```

### 3. PolicyClient Implementation

The `PolicyClient` sends HTTP POST to control-plane:

```python
# agent-sdk/org_agent_sdk/policy.py
def evaluate(self, policy_id: str, input_data: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{self.base_url}/policies/{policy_id}/evaluate",
        json=input_data,
        timeout=5,
    )
    result = response.json()
    # Returns: {"allowed": bool, "reason": str, "details": {...}}
    return result
```

### 4. Policy Evaluation (Rego)

The control-plane evaluates Rego policy:

```rego
# policies/payments/retry.rego
package payments.retry

default allow = false

allow {
    input.amount <= 10000
    input.previous_retries < 3
    not input.beneficiary_blocked
}

reason = "Amount exceeds limit" {
    input.amount > 10000
}

reason = "Too many previous retries" {
    input.previous_retries >= 3
}
```

### 5. Policy Result Examples

**Allowed:**
```json
{
  "allowed": true,
  "reason": "Policy allows retry",
  "details": {}
}
```

**Denied:**
```json
{
  "allowed": false,
  "reason": "Amount exceeds limit",
  "details": {
    "amount": 15000,
    "limit": 10000
  }
}
```

## Audit Logging Flow

### 1. What Gets Audited

The agent automatically audits:
- ✅ **Tool calls** - Every tool invocation
- ✅ **Policy checks** - Every policy evaluation
- ✅ **Decisions** - Every agent decision/action
- ✅ **LLM reasoning** - LLM suggestions and evidence

### 2. Audit Logging Points

#### A. Tool Call Auditing

**After fetching exception:**
```python
self.regulated.audit.log_tool_call(
    agent_id=self.regulated.agent_id,
    tool_name="get_payment_exception",
    args={"exception_id": exception_id},
    result_summary=exception_json[:200]
)
```

**After fetching customer:**
```python
self.regulated.audit.log_tool_call(
    agent_id=self.regulated.agent_id,
    tool_name="get_customer_profile",
    args={"customer_id": customer_id},
    result_summary=customer_json[:200]
)
```

**After suggesting resolution:**
```python
self.regulated.audit.log_tool_call(
    agent_id=self.regulated.agent_id,
    tool_name="suggest_payment_resolution",
    args={
        "exception_id": exception_id,
        "suggested_action": suggested_action
    },
    result_summary=resolution_json[:200]
)
```

**After executing retry:**
```python
self.regulated.audit.log_tool_call(
    agent_id=self.regulated.agent_id,
    tool_name="execute_payment_retry",
    args={
        "exception_id": exception_id,
        "amount": amount,
        "force": force
    },
    result_summary=retry_result_json[:200]
)
```

#### B. Policy Check Auditing

```python
self.regulated.audit.log_policy_check(
    agent_id=self.regulated.agent_id,
    policy_id="payments/retry",
    input_data={
        "amount": exception_data.get("amount", 0),
        "previous_retries": exception_data.get("retry_count", 0)
    },
    result=policy_result or {}
)
```

#### C. Decision Auditing

**After investigation:**
```python
decision = f"Investigated exception {exception_id}, LLM suggested {suggested_action} (confidence: {confidence:.2f})"
self.regulated.audit.log_decision(
    agent_id=self.regulated.agent_id,
    decision=decision,
    context={
        "exception_id": exception_id,
        "failure_reason": exception_data.get("failure_reason"),
        "suggested_action": suggested_action,
        "confidence": confidence,
        "evidence": evidence,
        "llm_reasoning": reasoning
    }
)
```

**After retry execution:**
```python
decision = f"Executed payment retry for exception {exception_id}. Status: {retry_result.get('status', 'unknown')}"
self.regulated.audit.log_decision(
    agent_id=self.regulated.agent_id,
    decision=decision,
    context={
        "exception_id": exception_id,
        "retry_result": retry_result,
        "force": force
    }
)
```

### 3. AuditClient Implementation

The `AuditClient` sends HTTP POST to control-plane:

```python
# agent-sdk/org_agent_sdk/audit.py
def log(self, agent_id: str, event_type: str, payload: dict[str, Any]) -> None:
    if not self._check_available():
        return  # Graceful degradation if control-plane unavailable
    
    requests.post(
        f"{self.base_url}/audit/entries",
        json={
            "agent_id": agent_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        },
        timeout=2,
    )
```

### 4. Audit Entry Format

**Tool Call Entry:**
```json
{
  "agent_id": "payment_failed",
  "event_type": "tool_call",
  "payload": {
    "tool_name": "get_payment_exception",
    "args": {"exception_id": "EX-2025-001"},
    "result_summary": "{\"exception_id\": \"EX-2025-001\", ...}"
  },
  "timestamp": "2025-02-04T14:30:22"
}
```

**Policy Check Entry:**
```json
{
  "agent_id": "payment_failed",
  "event_type": "policy_check",
  "payload": {
    "policy_id": "payments/retry",
    "input": {
      "amount": 5000.0,
      "previous_retries": 0
    },
    "result": {
      "allowed": true,
      "reason": "Policy allows retry"
    }
  },
  "timestamp": "2025-02-04T14:30:23"
}
```

**Decision Entry:**
```json
{
  "agent_id": "payment_failed",
  "event_type": "decision",
  "payload": {
    "decision": "Investigated exception EX-2025-001, LLM suggested retry (confidence: 0.85)",
    "context": {
      "exception_id": "EX-2025-001",
      "suggested_action": "retry",
      "confidence": 0.85,
      "evidence": ["Insufficient funds is temporary", "Customer has good payment history"],
      "llm_reasoning": {
        "decision": "retry",
        "confidence": 0.85,
        "evidence": [...]
      }
    }
  },
  "timestamp": "2025-02-04T14:30:24"
}
```

## Complete Flow Example

When you call `agent.retry_payment("EX-2025-001")`:

```
1. investigate_payment_exception() called
   ├─ Tool: get_payment_exception("EX-2025-001")
   │  └─ Audit: log_tool_call("get_payment_exception", ...)
   │
   ├─ Tool: get_customer_profile("CUST-001")
   │  └─ Audit: log_tool_call("get_customer_profile", ...)
   │
   ├─ LLM: reason(prompt) → {"decision": "retry", "confidence": 0.85, ...}
   │
   ├─ Policy: evaluate("payments/retry", {amount: 5000, ...})
   │  └─ Audit: log_policy_check("payments/retry", input, result)
   │  └─ Result: {"allowed": true, "reason": "Policy allows retry"}
   │
   ├─ Tool: suggest_payment_resolution(...)
   │  └─ Audit: log_tool_call("suggest_payment_resolution", ...)
   │
   └─ Audit: log_decision("Investigated exception...", context)

2. retry_payment() continues
   ├─ Tool: execute_payment_retry("EX-2025-001", ...)
   │  └─ Audit: log_tool_call("execute_payment_retry", ...)
   │
   └─ Audit: log_decision("Executed payment retry...", context)
```

## Viewing Audit Logs

### Via Control-Plane API

```bash
# Get all audit entries for payment_failed agent
curl http://localhost:8010/audit/entries?agent_id=payment_failed

# Get last 10 entries
curl http://localhost:8010/audit/entries?agent_id=payment_failed&limit=10
```

### Via Python

```python
import requests

# Get audit entries
response = requests.get(
    "http://localhost:8010/audit/entries",
    params={"agent_id": "payment_failed", "limit": 10}
)
entries = response.json()

for entry in entries:
    print(f"{entry['timestamp']} - {entry['event_type']}: {entry['payload']}")
```

## Demo: See Policy & Audit in Action

### 1. Start Control-Plane

```bash
cd agentic-factory-v1
python -m uvicorn control_plane.api.main:app --port 8010
```

### 2. Run Agent (in another terminal)

```bash
python -c "
from agents.payment_failed.agent import PaymentFailedAgent
agent = PaymentFailedAgent()
result = agent.retry_payment('EX-2025-001')
print(f'Retry status: {result[\"status\"]}')
"
```

### 3. View Audit Logs

```bash
curl http://localhost:8010/audit/entries?agent_id=payment_failed | jq
```

You'll see:
- Tool call entries
- Policy check entries
- Decision entries
- All with timestamps and full context

## Key Points

1. **Policy checks are automatic** - Happen when LLM suggests retry
2. **Policy can override LLM** - If policy denies, action is changed to "escalate"
3. **Everything is audited** - Tool calls, policy checks, decisions
4. **Audit is non-blocking** - If control-plane unavailable, agent continues (graceful degradation)
5. **Full context preserved** - Audit entries include all relevant data for compliance/review
