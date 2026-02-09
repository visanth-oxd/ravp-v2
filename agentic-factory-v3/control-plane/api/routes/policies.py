"""Policy Registry API – list policies, evaluate."""

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

# Add control-plane to path for imports
control_plane_dir = Path(__file__).resolve().parent.parent.parent
if str(control_plane_dir) not in sys.path:
    sys.path.insert(0, str(control_plane_dir))

from policy_registry.loader import evaluate, list_policies

router = APIRouter(prefix="/policies", tags=["policy-registry"])


@router.get("")
def list_policies_api():
    """
    List all registered policies.
    
    Returns:
        {"policies": [{"id": "...", "path": "..."}, ...]}
    """
    return {"policies": list_policies()}


@router.post("/{policy_id}/evaluate")
def evaluate_policy_api(policy_id: str, input_data: dict):
    """
    Evaluate a policy with input data.
    
    Args:
        policy_id: Policy identifier (e.g. "payments/retry")
        input_data: Input JSON for policy evaluation
    
    Returns:
        {"allowed": bool, "reason": str, "details": {...}}
    """
    result = evaluate(policy_id, input_data)
    
    # If policy not found, return 404
    if result.get("reason") == f"Policy not found: {policy_id}":
        raise HTTPException(
            status_code=404,
            detail=f"Policy not found: {policy_id}"
        )
    
    return result
