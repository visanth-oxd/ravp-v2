"""
Restart a GCE or Cloud SQL instance. Synthetic: records in healing_state.json.
Production: Compute API instances.reset() or Cloud SQL restart.
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "cloud_reliability"
_STATE_FILE = _DATA_DIR / "healing_state.json"


def restart_instance(instance_id: str) -> str:
    """
    Restart an instance. Demo: records last_restart in healing_state.json.
    Production: GCE instances.reset() or Cloud SQL instances.restart().
    """
    state = {}
    if _STATE_FILE.exists():
        try:
            with open(_STATE_FILE, "r") as f:
                state = json.load(f)
        except Exception:
            pass

    state["last_restart"] = {
        "instance_id": instance_id,
        "at": "2025-02-06T08:36:00Z",
        "status": "SUCCESS",
        "message": "Restart requested; in production this would call Compute/SQL API.",
    }

    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "instance_id": instance_id})

    return json.dumps({
        "instance_id": instance_id,
        "status": "SUCCESS",
        "message": "Instance restart requested. In production this would trigger a restart via GCP API.",
    }, indent=2)
