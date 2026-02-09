"""Tool Registry API – get/list tool definitions."""

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

# Add control-plane to path for imports
control_plane_dir = Path(__file__).resolve().parent.parent.parent
if str(control_plane_dir) not in sys.path:
    sys.path.insert(0, str(control_plane_dir))

from tool_registry.loader import get_tool, list_tools

router = APIRouter(prefix="/tools", tags=["tool-registry"])


@router.get("")
def list_tools_api():
    """
    List all registered tools.
    
    Returns:
        {"tools": [{tool definitions...}]}
    """
    return {"tools": list_tools()}


@router.get("/{tool_name}")
def get_tool_api(tool_name: str):
    """
    Get tool definition by name.
    
    Args:
        tool_name: Tool identifier
    
    Returns:
        Tool definition dict
    
    Raises:
        404: If tool not found
    """
    tool = get_tool(tool_name)
    if not tool:
        raise HTTPException(
            status_code=404,
            detail=f"Tool not found: {tool_name}"
        )
    return tool
