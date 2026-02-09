"""
Agent capability loader – builds context about other agents so an agent's LLM
can suggest when to invoke them (e.g. Reliability Agent suggesting Healing Agent).

Reads config/agent_invocation.yaml for invocable targets and config/agents/*.yaml
for each target's capability_for_other_agents. Used to make the platform
"intelligent" about deployed agents.
"""

from pathlib import Path
from typing import Any

import yaml


def _find_repo_root() -> Path:
    """Repo root from this file (agent-sdk/org_agent_sdk/agent_capabilities.py)."""
    return Path(__file__).resolve().parent.parent.parent


def _load_invocation_policy(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "config" / "agent_invocation.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("invocation_policy", {})


def _load_agent_definition(repo_root: Path, agent_id: str) -> dict[str, Any] | None:
    path = repo_root / "config" / "agents" / f"{agent_id}.yaml"
    if not path.exists():
        return None
    with open(path) as f:
        return yaml.safe_load(f) or {}


def get_all_agents_list(repo_root: Path | None = None) -> list[dict[str, Any]]:
    """
    List all agents registered in the mesh (config/agents/*.yaml).
    Returns list of dicts with agent_id, purpose, capability_for_other_agents, allowed_tools, domain.
    """
    repo_root = repo_root or _find_repo_root()
    agents_dir = repo_root / "config" / "agents"
    if not agents_dir.exists():
        return []
    out = []
    for path in sorted(agents_dir.glob("*.yaml")):
        agent_id = path.stem
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            continue
        purpose = data.get("purpose") or {}
        cap = data.get("capability_for_other_agents") or {}
        out.append({
            "agent_id": agent_id,
            "domain": data.get("domain"),
            "group": data.get("group"),
            "purpose": purpose.get("goal") or purpose.get("description") or "",
            "allowed_tools": data.get("allowed_tools") or data.get("tools") or [],
            "capability_for_other_agents": cap,
        })
    return out


def get_agent_mesh_card(repo_root: Path | None = None, agent_id: str = "") -> dict[str, Any] | None:
    """
    Get full mesh card for one agent (definition + capability). For discovery and mesh API.
    """
    repo_root = repo_root or _find_repo_root()
    data = _load_agent_definition(repo_root, agent_id)
    if not data:
        return None
    policy = _load_invocation_policy(repo_root)
    invocable = agent_id in policy
    allowed_callers = policy.get(agent_id, {}).get("allowed_callers", []) if invocable else []
    return {
        "agent_id": data.get("agent_id", agent_id),
        "domain": data.get("domain"),
        "group": data.get("group"),
        "purpose": data.get("purpose"),
        "allowed_tools": data.get("allowed_tools") or data.get("tools"),
        "capability_for_other_agents": data.get("capability_for_other_agents"),
        "invocable": invocable,
        "allowed_callers": allowed_callers,
        "version": data.get("version"),
    }


def _load_personas(repo_root: Path) -> dict[str, list[str]]:
    """Load persona -> list of allowed domain names from config/personas.yaml (domains or groups for backward compat)."""
    path = repo_root / "config" / "personas.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    personas = data.get("personas", {})
    out = {}
    for name, cfg in personas.items():
        if isinstance(cfg, dict):
            # Prefer domains; fall back to groups for backward compatibility
            if "domains" in cfg:
                out[name] = list(cfg["domains"])
            elif "groups" in cfg:
                out[name] = list(cfg["groups"])
        elif isinstance(cfg, list):
            out[name] = list(cfg)
    return out


def get_agents_for_persona(
    persona: str,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Return agents visible to the given persona (for UI and access control).
    Persona is defined in config/personas.yaml with a list of domains they can see.
    Platform (or empty domain list) sees all agents; others see only agents whose domain is in their list.
    """
    repo_root = repo_root or _find_repo_root()
    all_agents = get_all_agents_list(repo_root)
    personas = _load_personas(repo_root)
    allowed_domains = personas.get(persona)
    if allowed_domains is None:
        return []
    # Empty list means "see all" (e.g. platform)
    if not allowed_domains:
        return all_agents
    allowed_set = set(allowed_domains)
    return [a for a in all_agents if (a.get("domain") or "general") in allowed_set]


def get_agents_by_capability(
    capability: str,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Return agents that have the given capability (action name or keyword in summary/when_to_suggest).
    """
    repo_root = repo_root or _find_repo_root()
    all_agents = get_all_agents_list(repo_root)
    capability_lower = capability.lower()
    out = []
    for a in all_agents:
        cap = a.get("capability_for_other_agents") or {}
        actions = cap.get("actions") or []
        summary = (cap.get("summary") or a.get("purpose") or "").lower()
        when = (cap.get("when_to_suggest") or "").lower()
        action_names = [x.get("name", "").lower() if isinstance(x, dict) else str(x).lower() for x in actions]
        if (
            capability_lower in summary
            or capability_lower in when
            or capability_lower in action_names
            or any(capability_lower in an for an in action_names)
        ):
            out.append(a)
    return out


def get_invocable_agents_capabilities(
    repo_root: Path | None = None,
    caller_agent_id: str | None = None,
) -> str:
    """
    Build a single string describing invocable agents and when to suggest them.
    Use this as context for an agent's LLM so it can recommend invoking other agents.

    Args:
        repo_root: Optional repo root; default from __file__.
        caller_agent_id: If set, only include agents that this caller is allowed to invoke.

    Returns:
        Human-readable summary for LLM prompts, e.g. "Available agents you can suggest invoking: ..."
    """
    repo_root = repo_root or _find_repo_root()
    policy = _load_invocation_policy(repo_root)
    if not policy:
        return ""

    lines = [
        "Other deployed agents you can suggest invoking (when the situation fits):",
        "",
    ]
    for target_id, target_policy in policy.items():
        allowed = target_policy.get("allowed_callers", [])
        if caller_agent_id and caller_agent_id not in allowed:
            continue
        defn = _load_agent_definition(repo_root, target_id)
        if not defn:
            lines.append(f"- **{target_id}**: (no capability description in config)")
            lines.append("")
            continue
        cap = defn.get("capability_for_other_agents") or {}
        summary = cap.get("summary") or defn.get("purpose", {}).get("description") or defn.get("purpose", {}).get("goal") or "No description."
        when = cap.get("when_to_suggest", "")
        actions = cap.get("actions", [])
        name = defn.get("purpose", {}).get("goal") or target_id.replace("_", " ").title()
        lines.append(f"- **{name}** (agent_id: {target_id})")
        lines.append(f"  {summary}")
        if when:
            lines.append(f"  When to suggest: {when}")
        if actions:
            lines.append("  Actions:")
            for a in actions:
                if isinstance(a, dict):
                    lines.append(f"    - {a.get('name', '')}: {a.get('description', '')}")
                else:
                    lines.append(f"    - {a}")
        lines.append("")
    return "\n".join(lines).strip()


def get_invocable_agents_capabilities_list(
    repo_root: Path | None = None,
    caller_agent_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Same as get_invocable_agents_capabilities but returns a list of dicts
    (agent_id, summary, when_to_suggest, actions) for programmatic use.
    """
    repo_root = repo_root or _find_repo_root()
    policy = _load_invocation_policy(repo_root)
    if not policy:
        return []
    out = []
    for target_id, target_policy in policy.items():
        allowed = target_policy.get("allowed_callers", [])
        if caller_agent_id and caller_agent_id not in allowed:
            continue
        defn = _load_agent_definition(repo_root, target_id)
        cap = (defn or {}).get("capability_for_other_agents") or {}
        out.append({
            "agent_id": target_id,
            "summary": cap.get("summary") or (defn or {}).get("purpose", {}).get("description") or "",
            "when_to_suggest": cap.get("when_to_suggest", ""),
            "actions": cap.get("actions", []),
        })
    return out
