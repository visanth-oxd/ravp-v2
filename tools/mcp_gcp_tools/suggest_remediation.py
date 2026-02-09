"""
Suggest remediation for an incident using incident details, metrics, and logs (advisory only).
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "cloud_reliability"


def suggest_remediation(incident_id: str) -> str:
    """
    Suggest remediation steps for a cloud reliability incident.
    Uses incident context plus metrics and logs to produce advisory recommendations.

    In production, this could call an LLM or runbook API with incident context.
    This implementation uses synthetic data and rule-based suggestions for demo.

    Args:
        incident_id: Incident identifier (e.g. "INC-GCP-2025-001").

    Returns:
        JSON string with suggested actions and reasoning.
    """
    incidents_path = _DATA_DIR / "incidents.json"
    if not incidents_path.exists():
        return json.dumps({"error": "Incident data not found", "incident_id": incident_id})

    with open(incidents_path, "r") as f:
        incidents = json.load(f)

    incident = None
    for inc in incidents:
        if inc.get("incident_id") == incident_id:
            incident = inc
            break

    if not incident:
        return json.dumps({"error": "Incident not found", "incident_id": incident_id})

    # Rule-based suggestions based on known synthetic incident INC-GCP-2025-001
    suggestions = []
    symptoms = incident.get("symptoms", [])
    if any("latency" in s.lower() for s in symptoms) or any("5xx" in s for s in symptoms):
        suggestions.append({
            "action": "Check backend and Cloud SQL connectivity and scaling",
            "reason": "High latency and 5xx often indicate upstream timeouts or overload",
            "priority": "high",
        })
    if any("Cloud SQL" in s and "CPU" in s for s in symptoms):
        suggestions.append({
            "action": "Scale Cloud SQL (increase vCPUs) or optimize slow queries",
            "reason": "Sustained high Cloud SQL CPU can cause timeouts and cascading failures",
            "priority": "high",
        })
    if any("restart" in s.lower() for s in symptoms):
        suggestions.append({
            "action": "Review instance memory and health checks; consider OOM or liveness probe tuning",
            "reason": "Repeated restarts suggest OOM or failed health checks",
            "priority": "high",
        })
    suggestions.append({
        "action": "Review Cloud Logging for the affected resources in the incident time window",
        "reason": "Logs will show exact errors (e.g. OOMKilled, timeouts) to confirm root cause",
        "priority": "medium",
    })

    result = {
        "incident_id": incident_id,
        "suggestions": suggestions,
        "note": "Advisory only. Apply changes per change management and rollback plan.",
    }
    return json.dumps(result, indent=2)
