# Payment Failed Agent - Capabilities & Architecture

## What This Agent Does

The `PaymentFailedAgent` is a **single agent** that handles the **complete payment exception lifecycle**:

### 1. **Investigation** (`investigate_payment_exception`)
- Fetches payment exception data from PaymentProcessingSystem/TransactionEngine
- Fetches customer profile from CoreBankingSystem/CustomerDataSystem
- **Uses LLM to analyze** the exception and suggest resolution (retry/escalate/waive_fee)
- Checks policies if retry is suggested
- Returns investigation results with LLM reasoning

### 2. **Explanation** (`explain_payment_failure`)
- Runs investigation first
- **Uses LLM to generate** human-readable explanation
- Returns formatted explanation text

### 3. **Retry Execution** (`retry_payment`)
- **Automatically runs investigation** (unless `force=True`)
- **Uses LLM reasoning** from investigation to decide if retry is appropriate
- Checks policy if LLM suggests retry
- **Executes the retry** if LLM suggests it AND policy allows it
- Returns retry execution result

## Current Retry Flow (LLM-Driven)

```
User calls: retry_payment("EX-2025-001")
    ↓
1. investigate_payment_exception() is called automatically
    ↓
2. LLM analyzes exception + customer data
    ↓
3. LLM suggests action: "retry" | "escalate" | "waive_fee"
    ↓
4. If LLM suggests "retry":
    - Policy check runs
    - If policy allows → execute retry
    - If policy denies → escalate instead
    ↓
5. execute_payment_retry() tool is called
    ↓
6. Retry result returned
```

**Key Point:** The retry decision is **100% LLM-driven**. The agent uses LLM reasoning to decide whether to retry, then executes it.

## Do We Need a Separate Agent?

### Option 1: Single Agent (Current Approach) ✅
**Pros:**
- One agent handles full lifecycle (investigate → decide → execute)
- LLM reasoning is consistent across investigation and retry
- Simpler architecture
- All actions are audited together

**Cons:**
- Investigation always runs before retry (unless forced)
- Can't retry without investigation

### Option 2: Separate Agents
**Investigation Agent:**
- Only investigates and suggests
- No execution capability

**Retry Agent:**
- Only executes retries
- Requires investigation results as input
- Could have its own LLM reasoning for retry timing/strategy

**Pros:**
- Separation of concerns
- Can retry without full investigation
- Different LLM prompts for investigation vs retry

**Cons:**
- More complex architecture
- Need to pass data between agents
- More agents to manage

## Recommendation: Keep Single Agent (Current)

The current approach is **LLM-driven** and works well because:

1. **LLM decides retry** - The investigation uses LLM to analyze and suggest retry
2. **Policy enforces governance** - Policies act as safety net, not decision maker
3. **Single source of truth** - One agent, one audit trail
4. **Flexible** - Can force retry if needed (`force=True`)

## Making Retry More LLM-Driven (If Needed)

If you want retry to be **even more LLM-driven**, we could:

### Option A: Add LLM Retry Strategy
Have LLM decide not just "should we retry?" but also:
- When to retry (immediate vs delayed)
- Retry amount (full vs partial)
- Retry timing strategy

### Option B: Separate Retry Decision Method
```python
def should_retry_payment(self, exception_id: str) -> dict:
    """LLM-only method to decide if retry is appropriate."""
    # Lightweight LLM call, no full investigation
    # Returns: {"should_retry": True/False, "reason": "...", "confidence": 0.9}
```

### Option C: LLM-Driven Retry with Custom Strategy
```python
def retry_payment_with_strategy(self, exception_id: str) -> dict:
    """LLM decides retry strategy, then executes."""
    # LLM suggests: immediate retry, delayed retry, partial retry, etc.
    # Then executes based on LLM strategy
```

## Current Architecture Summary

```
PaymentFailedAgent (Single Agent)
├── investigate_payment_exception()
│   ├── Fetches data (tools)
│   ├── LLM reasoning (decision: retry/escalate/waive_fee)
│   ├── Policy check (governance)
│   └── Returns investigation result
│
├── explain_payment_failure()
│   ├── Runs investigation
│   ├── LLM generates explanation
│   └── Returns explanation text
│
└── retry_payment()
    ├── Runs investigation (LLM decides if retry is appropriate)
    ├── Validates LLM decision + policy
    ├── Executes retry (tool)
    └── Returns retry result
```

**Answer:** The agent **already retries based on LLM**. The LLM decides whether to retry during investigation, and `retry_payment()` executes it. No separate agent needed unless you want different LLM reasoning for retry vs investigation.
