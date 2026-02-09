# Quick Guide: Viewing Audit Logs

## Fix for zsh URL Issue

In zsh, you need to **quote the URL** when it contains `?`:

```bash
# ❌ Wrong (zsh interprets ? as glob)
curl http://localhost:8010/audit/entries?agent_id=payment_failed

# ✅ Correct (quoted URL)
curl "http://localhost:8010/audit/entries?agent_id=payment_failed"
```

## Step-by-Step: View Audit Logs

### 1. Start Control-Plane (Terminal 1)

```bash
cd agentic-factory-v1
python -m uvicorn control_plane.api.main:app --port 8010
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8010
```

### 2. Run Agent to Generate Audit Logs (Terminal 2)

```bash
cd agentic-factory-v1
export GOOGLE_API_KEY=your_key_here

python -c "
from agents.payment_failed.agent import PaymentFailedAgent
agent = PaymentFailedAgent()
result = agent.retry_payment('EX-2025-001')
print(f'Status: {result[\"status\"]}')
"
```

This will create audit entries.

### 3. View Audit Logs (Terminal 2)

```bash
# Get all entries for payment_failed agent
curl "http://localhost:8010/audit/entries?agent_id=payment_failed"

# Get last 10 entries (pretty print with jq if available)
curl "http://localhost:8010/audit/entries?agent_id=payment_failed&limit=10" | jq

# Or without jq
curl "http://localhost:8010/audit/entries?agent_id=payment_failed&limit=10" | python -m json.tool
```

## Alternative: Python Script

Create a simple script to view audit logs:

```python
# view_audit.py
import requests
import json

response = requests.get(
    "http://localhost:8010/audit/entries",
    params={"agent_id": "payment_failed", "limit": 10}
)

if response.status_code == 200:
    entries = response.json()
    for entry in entries:
        print(f"\n{entry['event_type'].upper()} - {entry.get('timestamp', 'N/A')}")
        print(json.dumps(entry['payload'], indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

Run it:
```bash
python view_audit.py
```

## Common Issues

### Issue: "Couldn't connect to server"
**Solution:** Start the control-plane server first (step 1 above)

### Issue: "zsh: no matches found"
**Solution:** Quote the URL: `curl "http://localhost:8010/audit/entries?agent_id=payment_failed"`

### Issue: Empty audit logs
**Solution:** Run the agent first to generate audit entries (step 2 above)
