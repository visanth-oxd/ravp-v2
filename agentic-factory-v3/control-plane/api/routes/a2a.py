"""
A2A (Agent2Agent) protocol endpoints.

Exposes invocable agents via A2A-style discovery (Agent Card) and task invocation.
Uses the existing AgentInvocationGateway for security and audit.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/a2a", tags=["a2a"])

# Repo root for loading gateway (when running from run_control_plane.py)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _get_gateway():
    """Load AgentInvocationGateway; requires repo root and agent-sdk on path."""
    import sys
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    if str(_REPO_ROOT / "agent-sdk") not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT / "agent-sdk"))
    try:
        from org_agent_sdk.agent_invocation import AgentInvocationGateway
        return AgentInvocationGateway()
    except ImportError as e:
        raise RuntimeError(f"A2A gateway unavailable: {e}") from e


def _load_invocation_policy():
    import yaml
    path = _REPO_ROOT / "config" / "agent_invocation.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("invocation_policy", {})


# ---- Agent Card (A2A discovery) ----
@router.get("/agents")
def list_agents():
    """List agent IDs that support A2A invocation (from invocation policy)."""
    policy = _load_invocation_policy()
    return {"agents": list(policy.keys())}


@router.get("/agents/{agent_id}/card")
def get_agent_card(agent_id: str):
    """
    Return A2A Agent Card for discovery.
    Describes identity, capabilities, and how to invoke (invoke endpoint).
    """
    policy = _load_invocation_policy()
    if agent_id not in policy:
        raise HTTPException(404, f"Unknown or non-invocable agent: {agent_id}")
    allowed = policy[agent_id].get("allowed_callers", [])
    # A2A Agent Card (simplified; full spec has more fields)
    return {
        "name": agent_id.replace("_", " ").title(),
        "agentId": agent_id,
        "description": "Invocable agent via Agent Factory; use POST /a2a/agents/{agent_id}/invoke with caller_agent_id, action, target_id, params.",
        "capabilities": {
            "actions": [
                "get_instance_details",
                "resize_cloud_sql_instance",
                "restart_instance",
            ] if agent_id == "cloud_healing" else [],
        },
        "allowedCallers": allowed,
        "invokeEndpoint": f"/a2a/agents/{agent_id}/invoke",
    }


# ---- Task invocation (A2A-style) ----
class InvokeRequest(BaseModel):
    caller_agent_id: str = Field(..., description="Agent ID of the caller (must be in allowed_callers)")
    action: str = Field(..., description="Action name, e.g. resize_cloud_sql_instance")
    target_type: str = Field(default="cloud_sql", description="Resource type")
    target_id: str = Field(..., description="Resource ID, e.g. cloud-sql-instance-1")
    params: dict = Field(default_factory=dict, description="Action parameters, e.g. {\"new_tier\": \"db-n1-standard-4\"}")


@router.post("/agents/{agent_id}/invoke")
def invoke_agent(agent_id: str, body: InvokeRequest):
    """
    Invoke the agent (A2A task). Uses AgentInvocationGateway; enforces allowlist and audit.
    """
    policy = _load_invocation_policy()
    if agent_id not in policy:
        raise HTTPException(404, f"Unknown or non-invocable agent: {agent_id}")
    gateway = _get_gateway()
    if not gateway.is_allowed(body.caller_agent_id, agent_id):
        raise HTTPException(403, f"Agent {body.caller_agent_id} is not allowed to invoke {agent_id}")
    result_json = gateway.invoke(
        caller_agent_id=body.caller_agent_id,
        target_agent_id=agent_id,
        action=body.action,
        target_type=body.target_type,
        target_id=body.target_id,
        params=body.params,
    )
    import json
    try:
        result = json.loads(result_json)
    except Exception:
        result = {"raw": result_json}
    return {
        "taskId": f"task-{agent_id}-{body.action}-{body.target_id}",
        "status": "completed",
        "result": result,
        "caller_agent_id": body.caller_agent_id,
        "target_agent_id": agent_id,
    }
