"""
List incidents (synthetic; production would use Incident Management / Monitoring API).

Used by the Incident Coordinator to find open or recent incidents.
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "cloud_reliability"


def list_incidents(status: str | None = None, limit: int = 20) -> str:
    """
    List incidents, optionally filtered by status.

    In production, this would call the Incident Management or Monitoring API
    to list incidents (open, resolved, etc.).

    Args:
        status: Optional filter: "open", "resolved", or None for all.
        limit: Max number of incidents to return (default 20).

    Returns:
        JSON string with list of incidents and count.
    """
    path = _DATA_DIR / "incidents.json"
    if not path.exists():
        return json.dumps({"error": "Incidents data not found", "incidents": [], "count": 0})

    with open(path, "r") as f:
        incidents = json.load(f)

    if status:
        status_lower = status.lower()
        incidents = [i for i in incidents if (i.get("status") or "").lower() == status_lower]
    incidents = incidents[:limit]

    return json.dumps({"incidents": incidents, "count": len(incidents)}, indent=2)
