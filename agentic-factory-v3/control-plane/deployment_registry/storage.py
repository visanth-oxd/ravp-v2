"""Deployment registry - tracks agent deployments across environments."""

import os
from pathlib import Path
from typing import Any, Optional, List, Dict
from datetime import datetime
import yaml


def get_deployments_dir() -> Path:
    """Get deployments directory path."""
    if os.environ.get("CONFIG_DIR"):
        config_dir = Path(os.environ["CONFIG_DIR"])
        if config_dir.name == "agents":
            return config_dir.parent / "deployments"
        return config_dir / "deployments"
    
    # Path: control-plane/deployment_registry/storage.py
    # Go up: storage -> deployment_registry -> control-plane -> repo root
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    return repo_root / "config" / "deployments"


def load_deployment(agent_id: str, environment: str) -> Optional[Dict[str, Any]]:
    """
    Load deployment record for an agent in an environment.
    
    Args:
        agent_id: Agent identifier
        environment: Environment name (e.g., "local", "dev", "prod", "gke-prod")
    
    Returns:
        Deployment record dict, or None if not found
    """
    deployments_dir = get_deployments_dir()
    path = deployments_dir / environment / f"{agent_id}.yaml"
    
    if not path.exists():
        return None
    
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def list_deployments(environment: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all deployments, optionally filtered by environment.
    
    Args:
        environment: Optional environment filter
    
    Returns:
        List of deployment records
    """
    deployments_dir = get_deployments_dir()
    
    if not deployments_dir.exists():
        return []
    
    deployments = []
    
    if environment:
        # List deployments in specific environment
        env_dir = deployments_dir / environment
        if env_dir.exists():
            for path in env_dir.glob("*.yaml"):
                agent_id = path.stem
                deployment = load_deployment(agent_id, environment)
                if deployment:
                    deployments.append(deployment)
    else:
        # List all deployments across all environments
        for env_dir in deployments_dir.iterdir():
            if env_dir.is_dir():
                env_name = env_dir.name
                for path in env_dir.glob("*.yaml"):
                    agent_id = path.stem
                    deployment = load_deployment(agent_id, env_name)
                    if deployment:
                        deployments.append(deployment)
    
    return deployments


def save_deployment(
    agent_id: str,
    environment: str,
    deployment_type: str,
    status: str,
    endpoint: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Save or update a deployment record.
    
    Args:
        agent_id: Agent identifier
        environment: Environment name
        deployment_type: Type of deployment ("local", "gke", "cloud_run", etc.)
        status: Deployment status ("deployed", "running", "stopped", "failed")
        endpoint: Optional endpoint URL
        metadata: Optional additional metadata (replicas, namespace, etc.)
    """
    deployments_dir = get_deployments_dir()
    env_dir = deployments_dir / environment
    env_dir.mkdir(parents=True, exist_ok=True)
    
    path = env_dir / f"{agent_id}.yaml"
    
    # Load existing if present
    existing = load_deployment(agent_id, environment) or {}
    
    deployment = {
        "agent_id": agent_id,
        "environment": environment,
        "deployment_type": deployment_type,
        "status": status,
        "endpoint": endpoint,
        "updated_at": datetime.utcnow().isoformat(),
        **(metadata or {}),
    }
    
    # Preserve created_at if exists
    if "created_at" in existing:
        deployment["created_at"] = existing["created_at"]
    else:
        deployment["created_at"] = datetime.utcnow().isoformat()
    
    with open(path, "w") as f:
        yaml.dump(deployment, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def delete_deployment(agent_id: str, environment: str) -> bool:
    """
    Delete a deployment record.
    
    Args:
        agent_id: Agent identifier
        environment: Environment name
    
    Returns:
        True if deleted, False if not found
    """
    deployments_dir = get_deployments_dir()
    path = deployments_dir / environment / f"{agent_id}.yaml"
    
    if path.exists():
        path.unlink()
        return True
    return False


def get_deployments_for_agent(agent_id: str) -> List[Dict[str, Any]]:
    """
    Get all deployments for a specific agent across all environments.
    
    Args:
        agent_id: Agent identifier
    
    Returns:
        List of deployment records
    """
    deployments = []
    deployments_dir = get_deployments_dir()
    
    if not deployments_dir.exists():
        return []
    
    for env_dir in deployments_dir.iterdir():
        if env_dir.is_dir():
            env_name = env_dir.name
            deployment = load_deployment(agent_id, env_name)
            if deployment:
                deployments.append(deployment)
    
    return deployments


def list_environments() -> List[str]:
    """
    List all environments that have deployments.
    
    Returns:
        List of environment names
    """
    deployments_dir = get_deployments_dir()
    
    if not deployments_dir.exists():
        return []
    
    return [d.name for d in deployments_dir.iterdir() if d.is_dir()]
