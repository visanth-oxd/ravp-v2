"""
Resize a Cloud SQL instance (change tier). Synthetic: writes healing_state.json for demo.
Production: Cloud SQL Admin API instances.patch() with settings.tier.
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "cloud_reliability"
_STATE_FILE = _DATA_DIR / "healing_state.json"

ALLOWED_TIERS = ("db-n1-standard-2", "db-n1-standard-4", "db-n1-standard-8", "db-n1-highmem-2", "db-n1-highmem-4")


def resize_cloud_sql_instance(instance_id: str, new_tier: str) -> str:
    """
    Resize Cloud SQL instance to a new tier. Demo: records the change in healing_state.json.
    Production: Cloud SQL Admin API instances.patch().
    """
    path = _DATA_DIR / "cloud_sql_instances.json"
    if not path.exists():
        return json.dumps({"error": "Instance data not found", "instance_id": instance_id})

    with open(path, "r") as f:
        instances = json.load(f)

    instance = None
    for inst in instances:
        if inst.get("instance_id") == instance_id:
            instance = inst
            break
    if not instance:
        return json.dumps({"error": "Instance not found", "instance_id": instance_id})

    old_tier = instance.get("tier", "unknown")
    if new_tier not in ALLOWED_TIERS:
        return json.dumps({
            "error": f"Tier not allowed. Allowed: {list(ALLOWED_TIERS)}",
            "instance_id": instance_id,
            "requested_tier": new_tier,
        })

    state = {}
    if _STATE_FILE.exists():
        try:
            with open(_STATE_FILE, "r") as f:
                state = json.load(f)
        except Exception:
            pass

    state["last_resize"] = {
        "instance_id": instance_id,
        "old_tier": old_tier,
        "new_tier": new_tier,
        "at": "2025-02-06T08:35:00Z",
        "status": "SUCCESS",
        "message": "Instance resize requested; in production this would call Cloud SQL Admin API.",
    }

    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "instance_id": instance_id})

    return json.dumps({
        "instance_id": instance_id,
        "old_tier": old_tier,
        "new_tier": new_tier,
        "status": "SUCCESS",
        "message": "Cloud SQL instance resize applied. In production this would trigger a resize via Cloud SQL Admin API.",
    }, indent=2)
