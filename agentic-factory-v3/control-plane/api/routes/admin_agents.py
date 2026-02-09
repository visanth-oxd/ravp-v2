"""Agent Registry Admin API: create/update/delete agent definitions via API."""

import sys
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

control_plane_dir = Path(__file__).resolve().parent.parent.parent
if str(control_plane_dir) not in sys.path:
    sys.path.insert(0, str(control_plane_dir))
from agent_registry.storage import load_agent, list_agents, save_agent, delete_agent, get_version_history
from agent_registry.rbac import get_user_from_token, can_edit_agent, can_delete_agent
from code_generator import generate_agent_code
from audit_store.storage import append as audit_append

# Import versioning functions (optional - for auto-versioning feature)
try:
    from agent_registry.versioning import detect_changes, calculate_new_version, create_changelog_entry
    VERSIONING_AVAILABLE = True
except ImportError:
    # Versioning not available - disable auto-versioning
    VERSIONING_AVAILABLE = False
    def detect_changes(*args, **kwargs):
        return {"major": [], "minor": [], "patch": []}
    def calculate_new_version(old_version, changes, auto_bump=True):
        return old_version, {}
    def create_changelog_entry(*args, **kwargs):
        return {}

from .auth import require_auth

router = APIRouter(prefix="/api/v2/agent-definitions", tags=["admin-agents"])


class Purpose(BaseModel):
    goal: str
    instructions_prefix: Optional[str] = None


class Owners(BaseModel):
    business: Optional[str] = None
    tech: Optional[str] = None
    risk: Optional[str] = None


class AgentDefinition(BaseModel):
    agent_id: str
    version: str = "1.0.0"
    domain: str = "general"
    risk_tier: str = "low"  # low | medium | high
    purpose: Purpose
    owners: Optional[Owners] = None
    allowed_tools: List[str] = []
    policies: List[str] = []
    model: Optional[str] = None
    llm_provider: Optional[str] = None  # google, vertex_ai, openai, anthropic
    llm_config: Optional[Dict[str, Any]] = None  # Provider-specific config
    confidence_threshold: Optional[float] = None
    human_in_the_loop: Optional[bool] = None


@router.get("")
def list_agent_definitions(_=Depends(require_auth)):
    """List all agent definitions."""
    agents = list_agents()
    return {"agents": agents}


@router.get("/{agent_id}")
def get_agent_definition(agent_id: str, _=Depends(require_auth)):
    """Get agent definition by ID."""
    definition = load_agent(agent_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return definition


@router.post("")
def create_agent_definition(
    definition: AgentDefinition,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    _=Depends(require_auth)
):
    """Create a new agent definition."""
    # Check if agent already exists
    existing = load_agent(definition.agent_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Agent already exists: {definition.agent_id}. Use PUT to update."
        )
    
    # Validate risk_tier
    if definition.risk_tier not in ["low", "medium", "high"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid risk_tier: {definition.risk_tier}. Must be one of: low, medium, high"
        )
    
    # Set creator in RBAC
    user = get_user_from_token(authorization, x_user_email)
    user_email = user.get("email", "")
    
    agent_dict = definition.model_dump(exclude_none=True)
    if "rbac" not in agent_dict:
        agent_dict["rbac"] = {}
    agent_dict["rbac"]["creator"] = user_email
    # Default visibility to public if not specified
    if "visibility" not in agent_dict["rbac"]:
        agent_dict["rbac"]["visibility"] = "public"
    
    # Save agent definition
    save_agent(definition.agent_id, agent_dict)
    
    # Audit log: Agent created
    audit_append(
        agent_id=definition.agent_id,
        event_type="agent_created",
        payload={
            "user": user_email,
            "agent_id": definition.agent_id,
            "version": definition.version,
            "domain": definition.domain,
            "risk_tier": definition.risk_tier,
            "allowed_tools": definition.allowed_tools,
            "policies": definition.policies,
            "model": definition.model
        }
    )
    
    # Auto-generate agent code from template
    code_generated = False
    code_message = ""
    code_path = None
    
    try:
        success, message, agent_dir = generate_agent_code(
            agent_id=definition.agent_id,
            agent_definition=agent_dict,
            overwrite=False
        )
        code_generated = success
        code_message = message
        code_path = agent_dir
        
        # Audit log: Code generation
        audit_append(
            agent_id=definition.agent_id,
            event_type="code_generated",
            payload={
                "user": user_email,
                "success": success,
                "path": agent_dir,
                "message": message
            }
        )
    except Exception as e:
        # Don't fail the whole request if code generation fails
        code_message = f"Agent definition created, but code generation failed: {e}"
        
        # Audit log: Code generation failed
        audit_append(
            agent_id=definition.agent_id,
            event_type="code_generation_failed",
            payload={
                "user": user_email,
                "error": str(e)
            }
        )
    
    return {
        "message": f"Agent '{definition.agent_id}' created",
        "agent": load_agent(definition.agent_id),
        "code_generation": {
            "success": code_generated,
            "message": code_message,
            "path": code_path
        }
    }


@router.put("/{agent_id}")
def update_agent_definition(
    agent_id: str, 
    definition: Dict[str, Any], 
    auto_version: bool = True,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    _=Depends(require_auth)
):
    """
    Update an existing agent definition with automatic versioning.
    
    Args:
        agent_id: Agent identifier
        definition: Updated agent definition (partial updates supported)
        auto_version: If True, automatically bump version based on changes
    
    The version will be automatically incremented based on changes:
    - MAJOR (2.0.0): risk_tier, purpose/goal, or domain changes
    - MINOR (1.1.0): tools or policies added/removed
    - PATCH (1.0.1): model, confidence_threshold, instructions, or other non-breaking changes
    """
    # Check if agent exists
    existing = load_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    
    # Check edit permission
    user = get_user_from_token(authorization)
    if not can_edit_agent(existing, user):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: You don't have permission to edit agent '{agent_id}'"
        )
    
    # Merge with existing definition (partial updates)
    merged_definition = existing.copy()
    merged_definition.update(definition)
    merged_definition["agent_id"] = agent_id
    
    # Ensure lists are properly set
    if "allowed_tools" in definition:
        merged_definition["allowed_tools"] = definition["allowed_tools"]
    if "policies" in definition:
        merged_definition["policies"] = definition["policies"]
    
    # Validate risk_tier if provided
    if "risk_tier" in merged_definition and merged_definition["risk_tier"] not in ["low", "medium", "high"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid risk_tier: {merged_definition['risk_tier']}. Must be one of: low, medium, high"
        )
    
    # Detect changes and calculate new version
    old_version = existing.get("version", "1.0.0")
    changes = detect_changes(existing, merged_definition)
    new_version, version_changes = calculate_new_version(old_version, changes, auto_bump=auto_version)
    
    # Update version in definition
    merged_definition["version"] = new_version
    
    # Add changelog entry if version changed or if there are changes
    if new_version != old_version or any(changes.values()):
        changelog_entry = create_changelog_entry(
            old_version, 
            new_version, 
            version_changes,
            user=None  # Could extract from auth token in future
        )
        
        # Add to changelog
        changelog = existing.get("changelog", [])
        changelog.append(changelog_entry)
        merged_definition["changelog"] = changelog
    
    # Save updated agent definition
    save_agent(agent_id, merged_definition, preserve_changelog=False)  # We're managing changelog ourselves
    
    updated_agent = load_agent(agent_id)
    
    return {
        "message": f"Agent '{agent_id}' updated",
        "version": {
            "old": old_version,
            "new": new_version,
            "changes": version_changes
        },
        "agent": updated_agent
    }


@router.get("/{agent_id}/history")
def get_agent_version_history(agent_id: str, _=Depends(require_auth)):
    """
    Get version history/changelog for an agent.
    
    Returns:
        List of version history entries showing what changed in each version
    """
    agent = load_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    
    history = get_version_history(agent_id)
    current_version = agent.get("version", "1.0.0")
    
    return {
        "agent_id": agent_id,
        "current_version": current_version,
        "history": history,
        "total_versions": len(history) + 1  # +1 for initial version
    }


@router.delete("/{agent_id}")
def delete_agent_definition(
    agent_id: str,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    _=Depends(require_auth)
):
    """Delete an agent definition and its generated code."""
    existing = load_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    
    # Check delete permission
    user = get_user_from_token(authorization, x_user_email)
    user_email = user.get("email", "")
    if not can_delete_agent(existing, user):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: You don't have permission to delete agent '{agent_id}'"
        )
    
    # Delete agent definition
    if not delete_agent(agent_id):
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    
    # Delete agent code directory
    code_deleted = False
    code_path = None
    try:
        # Get repo root (go up from control-plane/api/routes)
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        agent_dir = repo_root / "agents" / agent_id
        
        if agent_dir.exists() and agent_dir.is_dir():
            code_path = str(agent_dir)
            shutil.rmtree(agent_dir)
            code_deleted = True
    except Exception as e:
        # Don't fail the whole request if code deletion fails
        code_deleted = False
    
    # Audit log: Agent deleted
    audit_append(
        agent_id=agent_id,
        event_type="agent_deleted",
        payload={
            "user": user_email,
            "agent_id": agent_id,
            "domain": existing.get("domain"),
            "version": existing.get("version"),
            "code_deleted": code_deleted,
            "code_path": code_path
        }
    )
    
    return {
        "message": f"Agent '{agent_id}' deleted",
        "code_deleted": code_deleted,
        "code_path": code_path if code_deleted else None
    }


@router.put("/{agent_id}/rbac")
def update_agent_rbac(
    agent_id: str,
    rbac_update: Dict[str, Any],
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    _=Depends(require_auth)
):
    """
    Update RBAC permissions for an agent.
    
    Body:
    {
        "visibility": "public" | "domain" | "private" | "restricted",
        "allowed_users": ["user@example.com"],
        "allowed_roles": ["agent_user"],
        "allowed_domains": ["payments"]
    }
    """
    existing = load_agent(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    
    # Check edit permission
    user = get_user_from_token(authorization)
    if not can_edit_agent(existing, user):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: You don't have permission to edit RBAC for agent '{agent_id}'"
        )
    
    # Update RBAC settings
    if "rbac" not in existing:
        existing["rbac"] = {}
    
    if "visibility" in rbac_update:
        existing["rbac"]["visibility"] = rbac_update["visibility"]
    if "allowed_users" in rbac_update:
        existing["rbac"]["allowed_users"] = rbac_update["allowed_users"]
    if "allowed_roles" in rbac_update:
        existing["rbac"]["allowed_roles"] = rbac_update["allowed_roles"]
    if "allowed_domains" in rbac_update:
        existing["rbac"]["allowed_domains"] = rbac_update["allowed_domains"]
    
    # Save updated agent
    save_agent(agent_id, existing)
    
    return {
        "message": f"RBAC updated for agent '{agent_id}'",
        "rbac": existing["rbac"]
    }
