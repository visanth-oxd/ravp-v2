"""Load tool definitions from config/tool_registry.yaml or versioned config/tools/{domain}/{tool_id}/."""

import os
from pathlib import Path
from typing import Any

import yaml

# Optional versioned storage (preferred when present)
try:
    from .versioned_storage import (
        list_domains,
        list_tools_in_domain,
        load_tool_latest,
        TOOL_DOMAIN_MAP,
        get_tools_base_dir,
    )
    _VERSIONED_AVAILABLE = True
except ImportError:
    _VERSIONED_AVAILABLE = False


def get_tool_registry_path() -> Path:
    """
    Get path to tool registry YAML file.
    
    Uses CONFIG_DIR environment variable if set, otherwise defaults to
    repo_root/config/tool_registry.yaml relative to this file.
    """
    if os.environ.get("CONFIG_DIR"):
        # If CONFIG_DIR points to config/agents, go up one level
        config_dir = Path(os.environ["CONFIG_DIR"])
        if config_dir.name == "agents":
            return config_dir.parent / "tool_registry.yaml"
        return config_dir / "tool_registry.yaml"
    
    # Path: control-plane/tool_registry/loader.py
    # Go up: tool_registry -> control-plane -> repo root
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "config" / "tool_registry.yaml"


def load_tools() -> dict[str, Any]:
    """
    Load all tool definitions from YAML file.
    
    Returns:
        Dict with "tools" key containing tool definitions
    """
    path = get_tool_registry_path()
    if not path.exists():
        return {"tools": {}}
    
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    
    return data if "tools" in data else {"tools": {}}


def get_tool(tool_name: str) -> dict[str, Any] | None:
    """
    Get specific tool definition by name.
    Prefers versioned storage (config/tools/{domain}/{tool_id}/) when available.
    Searches all domains so UI-created tools in any domain are findable.
    """
    if _VERSIONED_AVAILABLE and get_tools_base_dir().exists():
        # Try known mapping first, then search all domains (for UI-created tools)
        for domain in [TOOL_DOMAIN_MAP.get(tool_name), None]:
            if domain is None:
                for domain_info in list_domains():
                    d = domain_info.get("domain", "")
                    latest = load_tool_latest(d, tool_name)
                    if latest:
                        latest.setdefault("name", tool_name)
                        return latest
                break
            latest = load_tool_latest(domain, tool_name)
            if latest:
                latest.setdefault("name", tool_name)
                return latest
    data = load_tools()
    tools = data.get("tools") or {}
    if tool_name not in tools:
        return None
    tool_def = dict(tools[tool_name])
    tool_def["name"] = tool_name
    return tool_def


def list_tools() -> list[dict[str, Any]]:
    """
    List all registered tools.
    Prefers versioned storage when available; merges with flat registry (versioned wins).
    """
    result_by_name: dict[str, dict[str, Any]] = {}
    if _VERSIONED_AVAILABLE and get_tools_base_dir().exists():
        for domain_info in list_domains():
            for t in list_tools_in_domain(domain_info["domain"]):
                name = t.get("tool_id") or t.get("name")
                if name:
                    t.setdefault("name", name)
                    result_by_name[name] = t
    data = load_tools()
    flat_tools = data.get("tools") or {}
    for tool_name, tool_def in flat_tools.items():
        if tool_name not in result_by_name:
            result_by_name[tool_name] = {"name": tool_name, **tool_def}
    return list(result_by_name.values())
