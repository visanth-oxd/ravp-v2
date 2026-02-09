# Cloud Reliability – Full scenario synthetic data

This folder holds synthetic data for a **single end-to-end scenario**: high latency and 5xx errors in us-central1 caused by Cloud SQL pressure and backend restarts.

## Scenario (INC-GCP-2025-001)

1. **Cloud SQL** (`cloud-sql-instance-1`) is on `db-n1-standard-2`. CPU and memory rise; connection count nears limit; disk read latency goes up; slow queries and connection pool exhaustion appear in logs.
2. **Backend** (`backend-service-us-central1-a-001`) times out talking to Cloud SQL, then restarts (health check failure, then OOM).
3. **API gateway** returns 504 and 5xx; P95 latency increases.

## Files

| File | Purpose |
|------|--------|
| `incidents.json` | INC-GCP-2025-001 (and a second resolved incident). |
| `metrics.json` | Time series: latency, error_rate, Cloud SQL cpu/memory/connections/disk_read_latency, instance_restarts. |
| `logs.json` | Cloud SQL logs (connection count, slow query, high CPU, disk latency, pool exhausted), backend timeouts/restarts/OOM, API gateway 504. |
| `cloud_sql_instances.json` | Instance(s) the **Healing Agent** can act on (tier, state, region). |
| `healing_state.json` | Written by healing tools (resize/restart) during demo; records last resize/restart. |

## Agent-to-agent flow

1. User asks Cloud Reliability Agent: **investigate INC-GCP-2025-001** or "What's wrong with INC-GCP-2025-001?"
2. Agent fetches incident, metrics, logs, and **suggest_remediation** (e.g. "Scale Cloud SQL", "Review instance memory").
3. User says **resize cloud sql** or **apply healing** (or "Scale the database to fix this").
4. Cloud Reliability Agent calls the **request_healing** tool, which invokes the **Cloud Healing Agent**.
5. Healing Agent runs **resize_cloud_sql_instance** (or **restart_instance**); demo writes to `healing_state.json`.

Run the interactive session: `python agents/cloud_reliability/interactive.py`
