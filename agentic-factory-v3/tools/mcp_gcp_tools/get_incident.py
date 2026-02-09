"""
Fetch incident/alert details (synthetic; production would use GCP Incident Management / Monitoring alerts).
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "cloud_reliability"


def get_incident(incident_id: str) -> str:
    """
    Fetch incident details by ID.

    In production, this would call:
    - GCP Incident Management / Monitoring API: incidents.get or similar
    - Or alerting policy violations from Cloud Monitoring

    Args:
        incident_id: Incident identifier (e.g. "INC-GCP-2025-001")

    Returns:
        JSON string of incident record, or error if not found
    """
    path = _DATA_DIR / "incidents.json"
    if not path.exists():
        return json.dumps({"error": "Data not found", "incident_id": incident_id})

    with open(path, "r") as f:
        records = json.load(f)

    for record in records:
        if record.get("incident_id") == incident_id:
            return json.dumps(record, indent=2)

    return json.dumps({"error": "Incident not found", "incident_id": incident_id})
