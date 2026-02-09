"""File-based agent registry storage. Reads from config/agents YAML files."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml


def get_config_dir() -> Path:
    """
    Get config directory path.
    
    Uses CONFIG_DIR environment variable if set, otherwise defaults to
    repo_root/config/agents relative to this file.
    """
    if os.environ.get("CONFIG_DIR"):
        return Path(os.environ["CONFIG_DIR"])
    
    # Path: control-plane/agent_registry/storage/file_storage.py
    # Go up: storage -> agent_registry -> control-plane -> repo root
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    return repo_root / "config" / "agents"


def load_agent(agent_id: str, version: Optional[str] = None) -> Optional[dict[str, Any]]:
    """
    Load agent definition by ID.
    
    Args:
        agent_id: Unique agent identifier (e.g. "payment_failed")
        version: Optional version (ignored for file-based storage - single file per agent)
    
    Returns:
        Agent definition dict, or None if not found
    """
    config_dir = get_config_dir()
    path = config_dir / f"{agent_id}.yaml"
    
    if not path.exists():
        return None
    
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    
    # Normalize to agent-definition-v1 schema
    # Handle legacy formats or missing fields
    if "tools" in data and "allowed_tools" not in data:
        data["allowed_tools"] = data["tools"]
    
    if "purpose" in data and isinstance(data["purpose"], str):
        data["purpose"] = {"goal": data["purpose"].strip()}
    
    if "version" not in data:
        data["version"] = "1.0.0"
    
    if "domain" not in data:
        data["domain"] = "payments"  # Default domain
    
    # When LLM is enabled (model set), interactive defaults to True
    if "interactive" not in data:
        model_id = data.get("model") or data.get("model_id")
        data["interactive"] = bool(model_id and str(model_id).strip())
    
    return data


def list_agents() -> list[dict[str, Any]]:
    """
    List all registered agents.
    
    Returns:
        List of dicts with agent_id and version
    """
    config_dir = get_config_dir()
    
    if not config_dir.exists():
        return []
    
    agents = []
    for path in config_dir.glob("*.yaml"):
        agent_id = path.stem
        definition = load_agent(agent_id)
        if definition:
            agents.append({
                "agent_id": agent_id,
                "version": definition.get("version", "1.0.0")
            })
    
    return agents


def save_agent(agent_id: str, definition: dict[str, Any], preserve_changelog: bool = True) -> None:
    """
    Save agent definition to YAML file.
    
    Args:
        agent_id: Unique agent identifier
        definition: Agent definition dict (will be validated/normalized)
        preserve_changelog: If True, preserve existing changelog entries
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Load existing agent to preserve changelog
    existing = load_agent(agent_id) if preserve_changelog else None
    existing_changelog = existing.get("changelog", []) if existing else []
    
    # Ensure agent_id matches
    definition = definition.copy()
    definition["agent_id"] = agent_id
    
    # Preserve changelog if it exists and we're not explicitly replacing it
    if preserve_changelog and existing_changelog and "changelog" not in definition:
        definition["changelog"] = existing_changelog
    
    # Ensure required fields have defaults
    if "version" not in definition:
        definition["version"] = "1.0.0"
    if "domain" not in definition:
        definition["domain"] = definition.get("domain", "general")
    if "risk_tier" not in definition:
        definition["risk_tier"] = "low"
    
    # Normalize purpose if it's a string
    if "purpose" in definition and isinstance(definition["purpose"], str):
        definition["purpose"] = {"goal": definition["purpose"].strip()}
    elif "purpose" not in definition:
        definition["purpose"] = {"goal": f"Agent {agent_id}"}
    
    # Normalize tools -> allowed_tools
    if "tools" in definition and "allowed_tools" not in definition:
        definition["allowed_tools"] = definition["tools"]
    elif "allowed_tools" not in definition:
        definition["allowed_tools"] = []
    
    # Ensure policies is a list
    if "policies" not in definition:
        definition["policies"] = []
    
    path = config_dir / f"{agent_id}.yaml"
    with open(path, "w") as f:
        yaml.dump(definition, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def get_version_history(agent_id: str) -> list[dict[str, Any]]:
    """
    Get version history/changelog for an agent.
    
    Args:
        agent_id: Unique agent identifier
    
    Returns:
        List of changelog entries (most recent first)
    """
    agent = load_agent(agent_id)
    if not agent:
        return []
    
    changelog = agent.get("changelog", [])
    # Return most recent first
    return sorted(changelog, key=lambda x: x.get("timestamp", ""), reverse=True) if changelog else []


def delete_agent(agent_id: str) -> bool:
    """
    Delete agent definition file.
    
    Args:
        agent_id: Unique agent identifier
    
    Returns:
        True if deleted, False if not found
    """
    config_dir = get_config_dir()
    path = config_dir / f"{agent_id}.yaml"
    
    if path.exists():
        path.unlink()
        return True
    return False
