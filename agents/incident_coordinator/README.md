# Incident Coordinator Agent

The **Incident Coordinator** finds incidents, understands their status, organizes meetings with humans and other agents, discusses defect resolution steps, and coordinates fixes (e.g. via the Healing Agent).

---

## Capabilities

| Capability | How |
|------------|-----|
| **Find incidents** | `list_incidents(status="open")` – lists open (or all) incidents from synthetic/API. |
| **Understand status** | `get_incident(incident_id)` – severity, affected services, symptoms, summary. |
| **Organize meetings** | `request_meeting(participants, title, agenda, incident_id)` – with humans (e.g. on-call) and/or agents (e.g. cloud_reliability). Synthetic: returns confirmation; production would create calendar/Meet events. |
| **Discuss resolution** | `get_log_entries`, `suggest_remediation`, plus LLM – discusses defect resolution and next steps. |
| **Fix issues** | `request_healing(action, target_id, new_tier)` – invokes the Cloud Healing Agent (resize, restart). **Human approval required** before execution. |

---

## Tools

- **list_incidents** – List incidents (open/resolved).
- **get_incident** – Get incident details.
- **get_log_entries** – Fetch logs for context.
- **get_metric_series** – Optional metrics context.
- **suggest_remediation** – Remediation suggestions for an incident.
- **request_meeting** – Request a meeting (participants, title, agenda).
- **request_healing** – Invoke Healing Agent (allowlisted in `config/agent_invocation.yaml`).

---

## Run interactively

From repo root:

```bash
python -m agents.incident_coordinator.interactive
```

Example prompts:

- **Find incidents:** `list open incidents` / `What open incidents do we have?`
- **Status:** `status INC-GCP-2025-001` / `What's the status of INC-GCP-2025-001?`
- **Organize meeting:** `schedule meeting with on-call and cloud_reliability` / `War room for INC-GCP-2025-001`
- **Resolution steps:** `resolution steps for INC-GCP-2025-001` / `Discuss defect resolution` / `How do we fix this?`
- **Fix (with approval):** `fix` / `invoke healing` → then type `approve` or `yes` to confirm, or `cancel`.

---

## Configuration

- **Agent definition:** `config/agents/incident_coordinator.yaml`
- **Invocation policy:** `incident_coordinator` is in `cloud_healing.allowed_callers` in `config/agent_invocation.yaml`, so the coordinator can request healing actions.
- **Synthetic data:** Incidents and logs come from `data/synthetic/cloud_reliability/` when GCP is not configured.
