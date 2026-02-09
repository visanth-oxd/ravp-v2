"""Agent Registry API – get/list agent definitions with RBAC."""

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Header

# Add control-plane to path for imports
control_plane_dir = Path(__file__).resolve().parent.parent.parent
if str(control_plane_dir) not in sys.path:
    sys.path.insert(0, str(control_plane_dir))

from agent_registry.storage import load_agent, list_agents
from agent_registry.rbac import (
    get_user_from_token,
    can_view_agent,
    can_use_agent,
    can_edit_agent,
    can_delete_agent,
    get_agent_permissions,
    filter_agents_by_permission,
)

router = APIRouter(prefix="/agents", tags=["agent-registry"])


@router.get("")
def list_agents_api(
    skill: Optional[str] = None,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email")
):
    """
    List all registered agents (filtered by RBAC permissions).
    
    Query params:
      - skill: optional skill filter (e.g. "incident_investigation")
    
    Returns:
        {"agents": [{"agent_id": "...", "version": "...", "permissions": {...}}, ...]}
    """
    user = get_user_from_token(authorization)
    all_agents = list_agents()
    
    # Load full definitions and filter by view permission
    agents_with_perms = []
    for agent_info in all_agents:
        agent_id = agent_info.get("agent_id")
        agent_def = load_agent(agent_id)
        if agent_def and can_view_agent(agent_def, user):
            # Filter by skill if specified
            if skill and skill not in agent_def.get("skills", []):
                continue
            
            perms = get_agent_permissions(agent_def, user)
            agents_with_perms.append({
                "agent_id": agent_id,
                "version": agent_info.get("version", "1.0.0"),
                "group": agent_def.get("group"),
                "domain": agent_def.get("domain"),
                "skills": agent_def.get("skills", []),
                "permissions": perms
            })
    
    return {"agents": agents_with_perms}


@router.get("/accessible")
def list_accessible_agents(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email")
):
    """
    List all agents the user can use (filtered by 'can_use' permission).
    
    Returns:
        {"agents": [{"agent_id": "...", "version": "...", "permissions": {...}}, ...]}
    """
    user = get_user_from_token(authorization)
    all_agents = list_agents()
    
    # Load full definitions and filter by use permission
    agents_with_perms = []
    for agent_info in all_agents:
        agent_id = agent_info.get("agent_id")
        agent_def = load_agent(agent_id)
        if agent_def and can_use_agent(agent_def, user):
            perms = get_agent_permissions(agent_def, user)
            agents_with_perms.append({
                "agent_id": agent_id,
                "version": agent_info.get("version", "1.0.0"),
                "group": agent_def.get("group"),
                "domain": agent_def.get("domain"),
                "permissions": perms
            })
    
    return {"agents": agents_with_perms}


@router.get("/{agent_id}")
def get_agent_api(
    agent_id: str,
    version: str | None = None,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email")
):
    """
    Get agent definition by ID (with RBAC check).
    
    Args:
        agent_id: Agent identifier
        version: Optional version (ignored for file-based storage)
        authorization: Authorization header for RBAC
    
    Returns:
        Agent definition dict
    
    Raises:
        404: If agent not found
        403: If user doesn't have permission to view
    """
    definition = load_agent(agent_id, version)
    if not definition:
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found: {agent_id}"
        )
    
    # Check view permission
    user = get_user_from_token(authorization, x_user_email)
    if not can_view_agent(definition, user):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: You don't have permission to view agent '{agent_id}'"
        )
    
    return definition


@router.get("/{agent_id}/permissions")
def get_agent_permissions_api(
    agent_id: str,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email")
):
    """
    Get user's permissions for an agent.
    
    Returns:
        {"agent_id": "...", "permissions": {"can_view": bool, "can_use": bool, ...}}
    """
    definition = load_agent(agent_id)
    if not definition:
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found: {agent_id}"
        )
    
    user = get_user_from_token(authorization, x_user_email)
    perms = get_agent_permissions(definition, user)
    
    return {
        "agent_id": agent_id,
        "permissions": perms
    }
