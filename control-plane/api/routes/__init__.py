"""API routes for control-plane services."""

from . import (
    agents,
    audit,
    kill_switch,
    policies,
    tools,
    auth,
    admin_tools,
    admin_policies,
    admin_agents,
    deployments,
    docker_build,
    gke_deploy,
    a2a,
    mesh,
    models,
    code_gen,
)

__all__ = [
    "agents",
    "audit",
    "kill_switch",
    "policies",
    "tools",
    "auth",
    "admin_tools",
    "admin_policies",
    "admin_agents",
    "deployments",
    "docker_build",
    "gke_deploy",
    "a2a",
    "mesh",
    "models",
    "code_gen",
]
