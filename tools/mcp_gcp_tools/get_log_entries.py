"""
Fetch log entries. Uses Cloud Logging API when GCP is configured; otherwise synthetic data.

Production: set GCP_PROJECT_ID (and optionally GOOGLE_APPLICATION_CREDENTIALS or ADC).
Install: pip install google-cloud-logging
"""

import json
import os
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "cloud_reliability"


def _fetch_from_cloud_logging(
    project_id: str,
    resource: str | None,
    severity: str | None,
    limit: int,
) -> str:
    """Call Cloud Logging API via google.cloud.logging."""
    try:
        from google.cloud import logging as cloud_logging
    except ImportError:
        return json.dumps({"error": "google-cloud-logging not installed. pip install google-cloud-logging"})

    client = cloud_logging.Client(project=project_id)
    # Build filter: https://cloud.google.com/logging/docs/view/logging-query-language
    filters = []
    if severity:
        filters.append(f'severity>="{severity}"')
    if resource:
        filters.append(f'resource.labels.resource_id="{resource}"')
    filter_str = " AND ".join(filters) if filters else None

    entries_list = []
    try:
        for entry in client.list_entries(
            resource_names=[f"projects/{project_id}"],
            filter_=filter_str,
            order_by="timestamp desc",
            page_size=limit,
        ):
            entries_list.append({
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                "severity": entry.severity,
                "resource": getattr(entry.resource, "labels", {}) or {},
                "text_payload": entry.text_payload,
                "json_payload": dict(entry.json_payload) if entry.json_payload else None,
            })
            if len(entries_list) >= limit:
                break
    except Exception as e:
        return json.dumps({"error": str(e), "entries": []})

    return json.dumps({"entries": entries_list, "count": len(entries_list)}, indent=2)


def get_log_entries(
    resource: str | None = None,
    severity: str | None = None,
    limit: int = 20,
) -> str:
    """
    Fetch log entries for troubleshooting.

    When GCP_PROJECT_ID is set and google-cloud-logging is installed, calls
    Cloud Logging API (entries.list). Otherwise uses synthetic data.

    Args:
        resource: Optional filter by resource (e.g. "backend-service-us-central1-a-001").
        severity: Optional filter by severity (e.g. "ERROR", "WARNING").
        limit: Max number of entries to return (default 20).

    Returns:
        JSON string of log entries.
    """
    project_id = os.environ.get("GCP_PROJECT_ID", "").strip()
    if project_id:
        return _fetch_from_cloud_logging(project_id, resource, severity, limit)

    path = _DATA_DIR / "logs.json"
    if not path.exists():
        return json.dumps({"error": "Logs data not found. Set GCP_PROJECT_ID for Cloud Logging.", "entries": []})

    with open(path, "r") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    if resource:
        entries = [e for e in entries if e.get("resource") == resource]
    if severity:
        entries = [e for e in entries if e.get("severity") == severity]
    entries = entries[:limit]

    return json.dumps({"entries": entries, "count": len(entries)}, indent=2)
