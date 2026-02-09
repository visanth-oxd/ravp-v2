"""Code Generation API - Generate agent implementation code from definitions."""

import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

control_plane_dir = Path(__file__).resolve().parent.parent.parent
if str(control_plane_dir) not in sys.path:
    sys.path.insert(0, str(control_plane_dir))

from code_generator import generate_agent_code, validate_agent_directory
from agent_registry.storage import load_agent
from .auth import require_auth
from audit_store.storage import append as audit_append

router = APIRouter(prefix="/api/v2/code-gen", tags=["code-generation"])


class GenerateCodeRequest(BaseModel):
    agent_id: str
    overwrite: bool = False


class GenerateCodeResponse(BaseModel):
    success: bool
    message: str
    agent_dir: Optional[str] = None
    agent_id: str


@router.post("/generate")
def generate_code(
    request: GenerateCodeRequest,
    _=Depends(require_auth)
) -> GenerateCodeResponse:
    """
    Generate agent implementation code from template.
    
    This endpoint:
    1. Loads the agent definition from config/agents/{agent_id}.yaml
    2. Generates Python code in agents/{agent_id}/ from the template
    3. Customizes the code with agent-specific details
    
    Args:
        agent_id: Agent identifier
        overwrite: If True, replace existing agent code
    
    Returns:
        Success status, message, and agent directory path
    """
    agent_id = request.agent_id
    
    # Load agent definition
    agent_def = load_agent(agent_id)
    if not agent_def:
        raise HTTPException(
            status_code=404,
            detail=f"Agent definition not found: {agent_id}. Create the agent definition first."
        )
    
    # Generate code
    success, message, agent_dir = generate_agent_code(
        agent_id=agent_id,
        agent_definition=agent_def,
        overwrite=request.overwrite
    )
    
    # Audit log
    audit_append(
        agent_id=agent_id,
        event_type="code_generated_manual",
        payload={
            "success": success,
            "overwrite": request.overwrite,
            "path": agent_dir,
            "message": message
        }
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return GenerateCodeResponse(
        success=success,
        message=message,
        agent_dir=agent_dir,
        agent_id=agent_id
    )


@router.get("/validate/{agent_id}")
def validate_code(
    agent_id: str,
    _=Depends(require_auth)
):
    """
    Check if agent implementation code exists.
    
    Returns:
        Status of agent code (exists or not)
    """
    exists, path_or_message = validate_agent_directory(agent_id)
    
    return {
        "agent_id": agent_id,
        "code_exists": exists,
        "path": path_or_message if exists else None,
        "message": "Agent code exists" if exists else "Agent code not found - generate it first"
    }


@router.post("/bulk-generate")
def bulk_generate_code(
    overwrite: bool = False,
    _=Depends(require_auth)
):
    """
    Generate code for all agent definitions that don't have implementation code.
    
    Useful for bulk setup or migration scenarios.
    """
    from agent_registry.storage import list_agents
    
    agents = list_agents()
    results = []
    
    for agent_id in agents:
        # Check if code already exists
        exists, _ = validate_agent_directory(agent_id)
        if exists and not overwrite:
            results.append({
                "agent_id": agent_id,
                "status": "skipped",
                "message": "Code already exists"
            })
            continue
        
        # Load definition and generate
        agent_def = load_agent(agent_id)
        if not agent_def:
            results.append({
                "agent_id": agent_id,
                "status": "error",
                "message": "Definition not found"
            })
            continue
        
        success, message, agent_dir = generate_agent_code(
            agent_id=agent_id,
            agent_definition=agent_def,
            overwrite=overwrite
        )
        
        results.append({
            "agent_id": agent_id,
            "status": "success" if success else "error",
            "message": message,
            "agent_dir": agent_dir
        })
    
    successful = sum(1 for r in results if r["status"] == "success")
    
    return {
        "total": len(results),
        "successful": successful,
        "failed": len(results) - successful,
        "results": results
    }
