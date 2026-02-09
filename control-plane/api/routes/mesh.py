"""
Agent mesh API – registry and capability-based discovery.

Exposes all registered agents and their capabilities so the platform has
a single view of "who is deployed" and "what can they do". Complements
the existing control-plane with mesh-style discovery.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/mesh", tags=["mesh"])

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _ensure_path():
    import sys
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    if str(_REPO_ROOT / "agent-sdk") not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT / "agent-sdk"))


# ---- List all agents ----
@router.get("/agents")
def list_agents(
    capability: str | None = Query(None, description="Filter agents that have this capability (action name or keyword)"),
    domain: str | None = Query(None, description="Filter agents by domain (e.g. payments, cloud_platform); used for UI grouping"),
    group: str | None = Query(None, description="Legacy: filter by group (prefer domain)"),
    persona: str | None = Query(None, description="Return only agents visible to this persona (config/personas.yaml uses domains); e.g. business, cloud, platform"),
):
    """
    List all agents registered in the mesh (config/agents).
    Optionally filter by capability, by domain, or by persona (persona-based visibility uses domains).
    """
    _ensure_path()
    from org_agent_sdk.agent_capabilities import (
        get_all_agents_list,
        get_agents_by_capability,
        get_agents_for_persona,
    )
    if persona:
        agents = get_agents_for_persona(persona, _REPO_ROOT)
    elif capability:
        agents = get_agents_by_capability(capability, _REPO_ROOT)
    else:
        agents = get_all_agents_list(_REPO_ROOT)
    if domain:
        agents = [a for a in agents if (a.get("domain") or "") == domain]
    elif group:
        agents = [a for a in agents if a.get("group") == group]
    return {
        "agents": [
            {"agent_id": a["agent_id"], "domain": a.get("domain"), "group": a.get("group"), "purpose": a.get("purpose", "")}
            for a in agents
        ],
        "count": len(agents),
    }


# ---- Get one agent (mesh card) ----
@router.get("/agents/{agent_id}")
def get_agent(agent_id: str):
    """
    Get full mesh card for an agent: definition, capability_for_other_agents,
    invocable status, and allowed_callers (if invocable).
    """
    _ensure_path()
    from org_agent_sdk.agent_capabilities import get_agent_mesh_card
    card = get_agent_mesh_card(_REPO_ROOT, agent_id)
    if not card:
        raise HTTPException(404, f"Agent not found: {agent_id}")
    return card
