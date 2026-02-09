"""
Request or schedule a meeting with humans and/or other agents (synthetic).

In production, this would integrate with Calendar, Google Meet, or a runbook
system to create events and notify participants.
"""

import json
from typing import List


def request_meeting(
    participants: str | List[str],
    title: str,
    agenda: str | None = None,
    incident_id: str | None = None,
) -> str:
    """
    Request a meeting with the given participants (humans and/or agent names).

    Synthetic: returns a confirmation message. In production, would create
    a calendar event and send invites.

    Args:
        participants: Comma-separated string or list of names (e.g. "on-call, cloud_reliability" or ["on-call", "cloud_reliability"]).
        title: Meeting title (e.g. "INC-GCP-2025-001 war room").
        agenda: Optional agenda or discussion points.
        incident_id: Optional incident ID this meeting is about.

    Returns:
        JSON string with status and details.
    """
    if isinstance(participants, str):
        parts = [p.strip() for p in participants.split(",") if p.strip()]
    else:
        parts = list(participants) if participants else []

    result = {
        "status": "requested",
        "message": f"Meeting requested: '{title}' with participants: {', '.join(parts) or 'none'}.",
        "title": title,
        "participants": parts,
        "agenda": agenda,
        "incident_id": incident_id,
        "note": "In production this would create a calendar event and send invites to humans and/or notify agent runbooks.",
    }
    return json.dumps(result, indent=2)
