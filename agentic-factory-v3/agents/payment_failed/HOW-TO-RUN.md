# How to Run the Payment Failed Agent

## Which LLM It Uses

The agent uses **Google Gemini** via the `google-genai` Python package:

- **Model**: `gemini-2.5-flash` (configured in `config/agents/payment_failed.yaml`)
- **API Package**: `google-genai` (new package) with fallback to deprecated `google-generativeai`
- **API Key**: Requires `GOOGLE_API_KEY` environment variable

### Model Configuration

The model is specified in the agent definition:

```yaml
# config/agents/payment_failed.yaml
model: gemini-2.5-flash
```

The `RegulatedAgent` SDK automatically:
1. Loads the agent definition
2. Reads the `model` field
3. Initializes `LLMClient` with that model
4. Uses it for all LLM operations (reasoning, explanations)

### LLM Usage Points

The agent uses LLM in three places:

1. **Investigation** (`investigate_payment_exception`):
   - LLM analyzes exception + customer data
   - Returns structured decision: `{"decision": "retry"|"escalate"|"waive_fee", "confidence": 0.85, "evidence": [...]}`

2. **Explanation** (`explain_payment_failure`):
   - LLM generates human-readable explanation
   - Returns natural language text

3. **Retry Decision** (`retry_payment`):
   - Uses LLM reasoning from investigation to decide if retry is appropriate

## How to Run the Agent

### Prerequisites

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set Google API key (REQUIRED for LLM)
export GOOGLE_API_KEY=your_google_api_key_here

# 3. Optional: Start control-plane (for policy/audit)
python run_control_plane.py
```

### Method 1: Interactive CLI (Easiest)

```bash
cd agentic-factory-v1
python agents/payment_failed/cli.py
```

Then use commands:
- `investigate EX-2025-001` - Investigate with LLM reasoning
- `explain EX-2025-001` - Get LLM-generated explanation
- `retry EX-2025-001` - Execute LLM-driven retry

### Method 2: Python Script

```bash
cd agentic-factory-v1
python agents/payment_failed/demo_payment_agent.py
```

This runs all demos automatically.

### Method 3: One-Liner Commands

```bash
cd agentic-factory-v1

# Investigate
python -c "
from agents.payment_failed.agent import PaymentFailedAgent
agent = PaymentFailedAgent()
result = agent.investigate_payment_exception('EX-2025-001')
print(f\"Suggested: {result['suggested_action']}, Confidence: {result['confidence']:.1%}\")
"

# Explain
python -c "
from agents.payment_failed.agent import PaymentFailedAgent
agent = PaymentFailedAgent()
print(agent.explain_payment_failure('EX-2025-001'))
"

# Retry
python -c "
from agents.payment_failed.agent import PaymentFailedAgent
agent = PaymentFailedAgent()
result = agent.retry_payment('EX-2025-001')
print(f\"Status: {result['status']}, Retry ID: {result.get('retry_id', 'N/A')}\")
"
```

### Method 4: Python REPL

```bash
cd agentic-factory-v1
python

>>> from agents.payment_failed.agent import PaymentFailedAgent
>>> agent = PaymentFailedAgent()
>>> result = agent.investigate_payment_exception("EX-2025-001")
>>> print(result['suggested_action'])
retry
>>> print(agent.explain_payment_failure("EX-2025-001"))
[LLM-generated explanation]
```

## LLM Initialization Flow

When you create `PaymentFailedAgent()`:

```
1. PaymentFailedAgent.__init__()
   ↓
2. RegulatedAgent.__init__(agent_id="payment_failed")
   ↓
3. Load agent definition from config/agents/payment_failed.yaml
   ↓
4. Read model: "gemini-2.5-flash"
   ↓
5. Initialize LLMClient(model_id="gemini-2.5-flash")
   ↓
6. Check GOOGLE_API_KEY environment variable
   ↓
7. Create genai.Client(api_key=GOOGLE_API_KEY)
   ↓
8. Store in self.regulated.llm
```

## Verifying LLM Setup

Check if LLM is available:

```python
from agents.payment_failed.agent import PaymentFailedAgent

agent = PaymentFailedAgent()

if agent.regulated.llm:
    print(f"✓ LLM initialized: {agent.regulated.llm.model_id}")
    print(f"  Using: google-genai API")
else:
    print("✗ LLM not available")
    print("  - Check GOOGLE_API_KEY is set")
    print("  - Check google-genai is installed: pip install google-genai")
```

## Changing the LLM Model

To use a different model, edit `config/agents/payment_failed.yaml`:

```yaml
# Change this line:
model: gemini-2.5-flash

# To any valid Gemini model:
# - gemini-2.5-flash (current, fast)
# - gemini-2.5-pro (more capable)
# - gemini-1.5-flash (older, fast)
# - gemini-1.5-pro (older, more capable)
```

Then restart the agent - it will automatically use the new model.

## Troubleshooting

### Error: "LLM not available"
- Set `GOOGLE_API_KEY` environment variable
- Install `google-genai`: `pip install google-genai`

### Error: "GOOGLE_API_KEY environment variable not set"
```bash
export GOOGLE_API_KEY=your_key_here
```

### Error: "google-genai not installed"
```bash
pip install google-genai
```

### Model not found error
- Check the model name is valid (e.g., `gemini-2.5-flash`)
- Check your API key has access to that model
- Try a different model name

## Summary

- **LLM**: Google Gemini (`gemini-2.5-flash`)
- **Package**: `google-genai` (with fallback to deprecated `google-generativeai`)
- **Config**: `config/agents/payment_failed.yaml` → `model: gemini-2.5-flash`
- **API Key**: `GOOGLE_API_KEY` environment variable
- **Usage**: Automatic - agent uses LLM for reasoning and explanations
