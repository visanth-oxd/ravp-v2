"""Kill-switch API – disable/enable agents and models."""

import sys
from pathlib import Path

from fastapi import APIRouter

# Add control-plane to path for imports
control_plane_dir = Path(__file__).resolve().parent.parent.parent
if str(control_plane_dir) not in sys.path:
    sys.path.insert(0, str(control_plane_dir))

from kill_switch.state import (
    disable_agent,
    disable_model,
    enable_agent,
    enable_model,
    is_agent_disabled,
    is_model_disabled,
    list_disabled,
)

router = APIRouter(prefix="/kill-switch", tags=["kill-switch"])


@router.get("")
def list_disabled_api():
    """
    List all disabled agents and models.
    
    Returns:
        {"agents": [...], "models": [...]}
    """
    return list_disabled()


@router.post("/agents/{agent_id}/disable")
def disable_agent_api(agent_id: str):
    """
    Disable an agent (prevent it from running).
    
    Args:
        agent_id: Agent identifier to disable
    
    Returns:
        {"agent_id": "...", "disabled": true}
    """
    disable_agent(agent_id)
    return {"agent_id": agent_id, "disabled": True}


@router.post("/agents/{agent_id}/enable")
def enable_agent_api(agent_id: str):
    """
    Enable an agent (allow it to run).
    
    Args:
        agent_id: Agent identifier to enable
    
    Returns:
        {"agent_id": "...", "disabled": false}
    """
    enable_agent(agent_id)
    return {"agent_id": agent_id, "disabled": False}


@router.get("/agents/{agent_id}")
def agent_status_api(agent_id: str):
    """
    Check if an agent is disabled.
    
    Args:
        agent_id: Agent identifier to check
    
    Returns:
        {"agent_id": "...", "disabled": true/false}
    """
    return {"agent_id": agent_id, "disabled": is_agent_disabled(agent_id)}


@router.post("/models/{model_id}/disable")
def disable_model_api(model_id: str):
    """
    Disable a model (prevent any agent from using it).
    
    Args:
        model_id: Model identifier to disable
    
    Returns:
        {"model_id": "...", "disabled": true}
    """
    disable_model(model_id)
    return {"model_id": model_id, "disabled": True}


@router.post("/models/{model_id}/enable")
def enable_model_api(model_id: str):
    """
    Enable a model (allow agents to use it).
    
    Args:
        model_id: Model identifier to enable
    
    Returns:
        {"model_id": "...", "disabled": false}
    """
    enable_model(model_id)
    return {"model_id": model_id, "disabled": False}


@router.get("/models/{model_id}")
def model_status_api(model_id: str):
    """
    Check if a model is disabled.
    
    Args:
        model_id: Model identifier to check
    
    Returns:
        {"model_id": "...", "disabled": true/false}
    """
    return {"model_id": model_id, "disabled": is_model_disabled(model_id)}
