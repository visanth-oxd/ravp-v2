"""Platform Admin: list/add/update/delete tools; versioned storage and domain grouping."""

import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Any, Optional
import yaml

control_plane_dir = Path(__file__).resolve().parent.parent.parent
if str(control_plane_dir) not in sys.path:
    sys.path.insert(0, str(control_plane_dir))
from tool_registry.loader import get_tool_registry_path, load_tools
from .auth import require_platform_admin

# Initialize router first to ensure it's always available
router = APIRouter(prefix="/api/v2/admin/tools", tags=["admin-tools"])

# Versioned storage and versioning logic (optional - graceful fallback)
_VERSIONED_AVAILABLE = False
TOOL_DOMAIN_MAP = {}

def get_tools_base_dir():
    """Fallback function for tools base directory."""
    return Path(__file__).resolve().parent.parent.parent / "config" / "tools"

# Initialize fallback functions
list_domains = None
list_tools_in_domain = None
load_tool_latest = None
load_tool_version = None
save_tool_version = None
update_tool_changelog = None
update_domain_registry = None
update_global_registry = None
get_tool_version_history = None
list_versions = None
migrate_flat_registry_to_versioned = None
detect_tool_changes = None
calculate_new_tool_version = None

try:
    from tool_registry.versioned_storage import (
        list_domains,
        list_tools_in_domain,
        load_tool_latest,
        load_tool_version,
        save_tool_version,
        update_tool_changelog,
        update_domain_registry,
        update_global_registry,
        get_tool_version_history,
        list_versions,
        TOOL_DOMAIN_MAP,
        get_tools_base_dir,
        migrate_flat_registry_to_versioned,
    )
    from tool_registry.tool_versioning import detect_tool_changes, calculate_new_tool_version
    _VERSIONED_AVAILABLE = True
except Exception as e:
    # Graceful fallback - versioned features disabled
    # Catch all exceptions to ensure module loads even if imports fail
    _VERSIONED_AVAILABLE = False
    TOOL_DOMAIN_MAP = {}
    # get_tools_base_dir already defined above as fallback


class ApiParamSpec(BaseModel):
    """Parameter for an API-based tool (path, query, or body)."""
    name: str
    param_in: str = "path"  # path | query | body
    required: bool = True
    description: Optional[str] = None


class ApiConfigSpec(BaseModel):
    """Configuration for a tool that calls an existing HTTP API."""
    method: str = "GET"  # GET, POST, PUT, PATCH, DELETE
    base_url_env: str = ""  # Env var name holding base URL, e.g. CUSTOMER_API_URL
    path_template: str = ""  # e.g. /users/{customer_id} or /v1/orders/{order_id}
    timeout_seconds: int = 10
    auth_header_env: Optional[str] = None  # Env var for Authorization header value
    api_key_header: Optional[str] = None  # Header name, e.g. X-Api-Key
    api_key_env: Optional[str] = None  # Env var for API key value
    parameters: List[ApiParamSpec] = []  # Parameters to substitute in path/query/body


class ToolDefinition(BaseModel):
    description: str
    data_sources: List[str] = []
    pii_level: str = "low"
    risk_tier: str = "low"
    requires_human_approval: bool = False
    domain: Optional[str] = None
    tool_id: Optional[str] = None
    implementation_type: Optional[str] = None  # "api" | "custom" (metadata-only or code)
    api_config: Optional[ApiConfigSpec] = None


def _save_tools(tools_dict: dict[str, Any]) -> None:
    path = get_tool_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump({"tools": tools_dict}, f, default_flow_style=False, sort_keys=False)


def _sync_tool_to_flat_registry(tool_id: str, definition: dict[str, Any]) -> None:
    """Update config/tool_registry.yaml so the tool is visible in the repo (flat registry)."""
    data = load_tools()
    tools = data.get("tools") or {}
    tools[tool_id] = {
        "description": definition.get("description", ""),
        "data_sources": definition.get("data_sources", []),
        "pii_level": definition.get("pii_level", "low"),
        "risk_tier": definition.get("risk_tier", "low"),
        "requires_human_approval": definition.get("requires_human_approval", False),
    }
    _save_tools(tools)


# ---------- Domain & versioned API ----------

@router.get("/domains")
def list_tool_domains(_=Depends(require_platform_admin)):
    """List all tool domains with tool counts (versioned storage)."""
    if not _VERSIONED_AVAILABLE or not get_tools_base_dir().exists():
        # Build from flat registry
        data = load_tools()
        tools = data.get("tools") or {}
        domains: dict[str, list] = {}
        for name in tools:
            domain = TOOL_DOMAIN_MAP.get(name, "general") if _VERSIONED_AVAILABLE else "general"
            domains.setdefault(domain, []).append({"tool_id": name, "version": "1.0.0"})
        return {
            "domains": [
                {"domain": d, "tool_count": len(t), "tools": t}
                for d, t in sorted(domains.items())
            ]
        }
    if _VERSIONED_AVAILABLE and 'list_domains' in globals() and callable(list_domains):
        return {"domains": list_domains()}
    return {"domains": []}


@router.get("/by-domain/{domain}")
def list_tools_by_domain(domain: str, _=Depends(require_platform_admin)):
    """List all tools in a domain (with versions)."""
    if _VERSIONED_AVAILABLE and list_tools_in_domain and get_tools_base_dir().exists():
        tools = list_tools_in_domain(domain)
        return {"domain": domain, "tools": tools}
    data = load_tools()
    flat = data.get("tools") or {}
    tools = [
        {"name": n, "tool_id": n, "domain": domain, "version": "1.0.0", **d}
        for n, d in flat.items()
        if not _VERSIONED_AVAILABLE or TOOL_DOMAIN_MAP.get(n, "general") == domain
    ]
    if _VERSIONED_AVAILABLE and not tools and domain != "general":
        tools = [
            {"name": n, "tool_id": n, "domain": domain, "version": "1.0.0", **d}
            for n, d in flat.items()
        ]
    return {"domain": domain, "tools": tools}


@router.get("/by-domain/{domain}/{tool_id}")
def get_tool_by_domain(domain: str, tool_id: str, version: Optional[str] = Query(None), _=Depends(require_platform_admin)):
    """Get tool by domain and id (optional version)."""
    if _VERSIONED_AVAILABLE and load_tool_latest and load_tool_version and get_tools_base_dir().exists():
        if version:
            t = load_tool_version(domain, tool_id, version)
        else:
            t = load_tool_latest(domain, tool_id)
        if t:
            return t
        raise HTTPException(status_code=404, detail=f"Tool not found: {domain}/{tool_id}")
    data = load_tools()
    tools = data.get("tools") or {}
    if tool_id not in tools:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    return {"name": tool_id, "tool_id": tool_id, "domain": domain, "version": "1.0.0", **tools[tool_id]}


@router.get("/by-domain/{domain}/{tool_id}/versions")
def get_tool_versions(domain: str, tool_id: str, _=Depends(require_platform_admin)):
    """List all versions for a tool."""
    if not _VERSIONED_AVAILABLE or not list_versions:
        return {"domain": domain, "tool_id": tool_id, "versions": ["1.0.0"]}
    vers = list_versions(domain, tool_id)
    if not vers:
        raise HTTPException(status_code=404, detail=f"Tool not found: {domain}/{tool_id}")
    return {"domain": domain, "tool_id": tool_id, "versions": vers}


@router.get("/by-domain/{domain}/{tool_id}/history")
def get_tool_history(domain: str, tool_id: str, _=Depends(require_platform_admin)):
    """Get version history (changelog) for a tool."""
    if not _VERSIONED_AVAILABLE or not get_tool_version_history:
        return {"domain": domain, "tool_id": tool_id, "history": []}
    history = get_tool_version_history(domain, tool_id)
    return {"domain": domain, "tool_id": tool_id, "history": history}


@router.post("/migrate")
def migrate_tools(_=Depends(require_platform_admin)):
    """One-time: migrate flat tool_registry.yaml to versioned structure."""
    if not _VERSIONED_AVAILABLE or not migrate_flat_registry_to_versioned:
        raise HTTPException(status_code=501, detail="Versioned storage not available")
    count = migrate_flat_registry_to_versioned(get_tool_registry_path, load_tools)
    return {"message": f"Migrated {count} tools to versioned storage", "migrated": count}


class CreateToolRequest(BaseModel):
    """Request body for creating a new tool (e.g. API-based)."""
    tool_id: str
    description: str
    data_sources: List[str] = []
    pii_level: str = "low"
    risk_tier: str = "low"
    requires_human_approval: bool = False
    implementation_type: Optional[str] = None  # "api" | "custom"
    api_config: Optional[ApiConfigSpec] = None


@router.post("/by-domain/{domain}")
def create_tool_in_domain(
    domain: str,
    body: CreateToolRequest,
    _=Depends(require_platform_admin),
):
    """Create a new tool in the given domain (version 1.0.0). Use for API-based tools or metadata-only."""
    if not _VERSIONED_AVAILABLE or not save_tool_version or not update_tool_changelog or not update_domain_registry or not update_global_registry:
        raise HTTPException(status_code=501, detail="Versioned storage not available")
    base = get_tools_base_dir()
    base.mkdir(parents=True, exist_ok=True)
    tool_id = body.tool_id.strip()
    if not tool_id:
        raise HTTPException(status_code=400, detail="tool_id is required")
    if load_tool_latest and load_tool_latest(domain, tool_id):
        raise HTTPException(status_code=400, detail=f"Tool already exists: {domain}/{tool_id}")
    payload = body.model_dump(exclude_none=True)
    payload.setdefault("domain", domain)
    save_tool_version(domain, tool_id, "1.0.0", payload, created_by="admin")
    update_tool_changelog(domain, tool_id, "1.0.0", None, {"initial": ["Initial version"]}, created_by="admin")
    update_domain_registry(domain)
    update_global_registry()
    _sync_tool_to_flat_registry(tool_id, payload)
    return {"message": f"Tool '{tool_id}' created in domain '{domain}'", "version": "1.0.0", "tool": load_tool_latest(domain, tool_id)}


@router.put("/by-domain/{domain}/{tool_id}")
def update_tool_versioned(
    domain: str,
    tool_id: str,
    definition: ToolDefinition,
    _=Depends(require_platform_admin),
):
    """Update tool (creates new version, writes to repo)."""
    if not _VERSIONED_AVAILABLE or not load_tool_latest or not save_tool_version or not detect_tool_changes or not calculate_new_tool_version:
        raise HTTPException(status_code=501, detail="Versioned storage not available")
    base = get_tools_base_dir()
    base.mkdir(parents=True, exist_ok=True)
    payload = definition.model_dump(exclude_none=True)
    payload.setdefault("tool_id", tool_id)
    payload.setdefault("domain", domain)
    old = load_tool_latest(domain, tool_id)
    if not old:
        # Create new tool at 1.0.0
        save_tool_version(domain, tool_id, "1.0.0", payload, created_by="admin")
        update_tool_changelog(domain, tool_id, "1.0.0", None, {"initial": ["Initial version"]}, created_by="admin")
        update_domain_registry(domain)
        update_global_registry()
        _sync_tool_to_flat_registry(tool_id, payload)
        return {"message": f"Tool '{tool_id}' created", "version": "1.0.0", "tool": load_tool_latest(domain, tool_id)}
    old_ver = old.get("version", "1.0.0")
    old_def = {k: old.get(k) for k in ["description", "data_sources", "pii_level", "risk_tier", "requires_human_approval"]}
    new_def = {
        "description": payload.get("description", ""),
        "data_sources": payload.get("data_sources", []),
        "pii_level": payload.get("pii_level", "low"),
        "risk_tier": payload.get("risk_tier", "low"),
        "requires_human_approval": payload.get("requires_human_approval", False),
    }
    if payload.get("implementation_type") is not None:
        new_def["implementation_type"] = payload["implementation_type"]
    if payload.get("api_config") is not None:
        new_def["api_config"] = payload["api_config"]
    changes = detect_tool_changes(old_def, new_def)
    new_ver, _ = calculate_new_tool_version(old_ver, changes, auto_bump=True)
    save_tool_version(domain, tool_id, new_ver, new_def, created_by="admin")
    update_tool_changelog(domain, tool_id, new_ver, old_ver, changes, created_by="admin")
    update_domain_registry(domain)
    update_global_registry()
    _sync_tool_to_flat_registry(tool_id, new_def)
    return {
        "message": f"Tool '{tool_id}' updated",
        "version_change": {"old": old_ver, "new": new_ver},
        "tool": load_tool_latest(domain, tool_id),
    }


# ---------- Legacy flat API (backward compat) ----------

@router.get("")
def list_tools_admin(domain: Optional[str] = Query(None), _=Depends(require_platform_admin)):
    """List all tools; optional ?domain= to filter by domain."""
    if domain and _VERSIONED_AVAILABLE and list_tools_in_domain and get_tools_base_dir().exists():
        tools = list_tools_in_domain(domain)
        return {"tools": tools, "domain": domain}
    data = load_tools()
    flat = data.get("tools") or {}
    if domain and _VERSIONED_AVAILABLE:
        flat = {n: d for n, d in flat.items() if TOOL_DOMAIN_MAP.get(n, "general") == domain}
    return {"tools": flat}


@router.post("/{tool_name}")
def add_tool(tool_name: str, definition: ToolDefinition, _=Depends(require_platform_admin)):
    data = load_tools()
    tools = data.get("tools") or {}
    if tool_name in tools:
        raise HTTPException(status_code=400, detail=f"Tool already exists: {tool_name}")
    tools[tool_name] = definition.model_dump(exclude_none=True)
    _save_tools(tools)
    return {"message": f"Tool '{tool_name}' added", "tool": tools[tool_name]}


@router.put("/{tool_name}")
def update_tool(tool_name: str, definition: ToolDefinition, _=Depends(require_platform_admin)):
    data = load_tools()
    tools = data.get("tools") or {}
    if tool_name not in tools:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    tools[tool_name] = definition.model_dump(exclude_none=True)
    _save_tools(tools)
    return {"message": f"Tool '{tool_name}' updated"}


@router.delete("/{tool_name}")
def delete_tool(tool_name: str, _=Depends(require_platform_admin)):
    data = load_tools()
    tools = data.get("tools") or {}
    if tool_name not in tools:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    del tools[tool_name]
    _save_tools(tools)
    return {"message": f"Tool '{tool_name}' deleted"}
