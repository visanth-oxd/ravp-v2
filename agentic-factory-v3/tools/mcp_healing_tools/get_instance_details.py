"""
Get Cloud SQL (or compute) instance details. Synthetic; production would use GCP SQL Admin / Compute API.
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic" / "cloud_reliability"
_STATE_FILE = _DATA_DIR / "healing_state.json"


def _load_state():
    if _STATE_FILE.exists():
        try:
            with open(_STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_instance_details(instance_id: str) -> str:
    """
    Fetch instance details (Cloud SQL or GCE). For demo, reads from cloud_sql_instances.json.
    In production: Cloud SQL Admin API instances.get() or Compute API instances.get().
    """
    path = _DATA_DIR / "cloud_sql_instances.json"
    if not path.exists():
        return json.dumps({"error": "Instance data not found", "instance_id": instance_id})

    with open(path, "r") as f:
        instances = json.load(f)

    state = _load_state()
    for inst in instances:
        if inst.get("instance_id") == instance_id:
            out = dict(inst)
            if state.get("last_resize", {}).get("instance_id") == instance_id:
                out["tier"] = state["last_resize"].get("new_tier", out["tier"])
                out["last_healing_action"] = state["last_resize"]
            return json.dumps(out, indent=2)

    return json.dumps({"error": "Instance not found", "instance_id": instance_id})
