"""Versioned tool storage: config/tools/{domain}/{tool_id}/{version}.yaml with domain registries."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# Domain mapping: tool_id -> domain (for migration and grouping)
TOOL_DOMAIN_MAP = {
    "get_payment_exception": "payments",
    "suggest_payment_resolution": "payments",
    "execute_payment_retry": "payments",
    "get_customer_profile": "customer",
    "summarise_text": "general",
    "get_transaction_history": "fraud",
    "check_risk_score": "fraud",
    "flag_suspicious_account": "fraud",
}


def get_tools_base_dir() -> Path:
    """Base directory for versioned tools: config/tools."""
    if os.environ.get("CONFIG_DIR"):
        config_dir = Path(os.environ["CONFIG_DIR"])
        if config_dir.name == "agents":
            return config_dir.parent / "tools"
        return config_dir / "tools"
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "config" / "tools"


def get_tool_dir(domain: str, tool_id: str) -> Path:
    """Directory for a tool: config/tools/{domain}/{tool_id}."""
    return get_tools_base_dir() / domain / tool_id


def get_domain_registry_path(domain: str) -> Path:
    """Path to domain registry: config/tools/{domain}/_registry.yaml."""
    return get_tools_base_dir() / domain / "_registry.yaml"


def get_global_registry_path() -> Path:
    """Path to global registry: config/tools/_global_registry.yaml."""
    return get_tools_base_dir() / "_global_registry.yaml"


def load_tool_version(domain: str, tool_id: str, version: str) -> dict[str, Any] | None:
    """Load a specific tool version from file."""
    version_file = get_tool_dir(domain, tool_id) / f"{version}.yaml"
    if not version_file.exists():
        return None
    with open(version_file, "r") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("name", tool_id)
    data.setdefault("tool_id", tool_id)
    data.setdefault("domain", domain)
    data.setdefault("version", version)
    return data


def get_latest_version(domain: str, tool_id: str) -> str | None:
    """Get latest version string for a tool (from directory or changelog)."""
    tool_dir = get_tool_dir(domain, tool_id)
    if not tool_dir.exists():
        return None
    versions = []
    for f in tool_dir.iterdir():
        if f.suffix == ".yaml" and f.stem != "changelog" and not f.name.startswith("_"):
            versions.append(f.stem)
    if not versions:
        return None
    # Sort semantic versions
    def parse(v: str) -> tuple:
        parts = v.split(".")
        return (int(parts[0]) if len(parts) > 0 else 0,
                int(parts[1]) if len(parts) > 1 else 0,
                int(parts[2]) if len(parts) > 2 else 0)
    try:
        versions.sort(key=parse)
        return versions[-1]
    except (ValueError, IndexError):
        return versions[-1] if versions else None


def load_tool_latest(domain: str, tool_id: str) -> dict[str, Any] | None:
    """Load latest version of a tool."""
    version = get_latest_version(domain, tool_id)
    if not version:
        return None
    return load_tool_version(domain, tool_id, version)


def save_tool_version(
    domain: str,
    tool_id: str,
    version: str,
    definition: dict[str, Any],
    created_by: str | None = None,
) -> None:
    """Save a tool version to file (repo sync). Includes api_config for API-based tools."""
    tool_dir = get_tool_dir(domain, tool_id)
    tool_dir.mkdir(parents=True, exist_ok=True)
    out = {
        "tool_id": tool_id,
        "domain": domain,
        "version": version,
        "description": definition.get("description", ""),
        "data_sources": definition.get("data_sources", []),
        "pii_level": definition.get("pii_level", "low"),
        "risk_tier": definition.get("risk_tier", "low"),
        "requires_human_approval": definition.get("requires_human_approval", False),
    }
    if definition.get("implementation_type"):
        out["implementation_type"] = definition["implementation_type"]
    if definition.get("api_config"):
        out["api_config"] = definition["api_config"]
    out["metadata"] = {
        "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created_by": created_by or "admin",
    }
    version_file = tool_dir / f"{version}.yaml"
    with open(version_file, "w") as f:
        yaml.dump(out, f, default_flow_style=False, sort_keys=False)


def update_tool_changelog(
    domain: str,
    tool_id: str,
    version: str,
    previous_version: str | None,
    changes: dict[str, list],
    created_by: str | None = None,
) -> None:
    """Append to changelog.yaml for the tool."""
    tool_dir = get_tool_dir(domain, tool_id)
    changelog_file = tool_dir / "changelog.yaml"
    if changelog_file.exists():
        with open(changelog_file, "r") as f:
            changelog = yaml.safe_load(f) or {"versions": []}
    else:
        changelog = {"versions": []}
    entry = {
        "version": version,
        "previous_version": previous_version,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "changed_by": created_by or "admin",
        "changes": changes,
    }
    changelog.setdefault("versions", []).append(entry)
    with open(changelog_file, "w") as f:
        yaml.dump(changelog, f, default_flow_style=False, sort_keys=False)


def get_tool_version_history(domain: str, tool_id: str) -> list[dict[str, Any]]:
    """Return version history for a tool (from changelog)."""
    changelog_file = get_tool_dir(domain, tool_id) / "changelog.yaml"
    if not changelog_file.exists():
        return []
    with open(changelog_file, "r") as f:
        changelog = yaml.safe_load(f) or {}
    return changelog.get("versions", [])


def list_versions(domain: str, tool_id: str) -> list[str]:
    """List all version strings for a tool."""
    tool_dir = get_tool_dir(domain, tool_id)
    if not tool_dir.exists():
        return []
    versions = []
    for f in tool_dir.iterdir():
        if f.suffix == ".yaml" and f.stem != "changelog" and not f.name.startswith("_"):
            versions.append(f.stem)
    def key(v):
        parts = v.split(".")
        return (int(parts[0]) if len(parts) > 0 else 0,
                int(parts[1]) if len(parts) > 1 else 0,
                int(parts[2]) if len(parts) > 2 else 0)
    try:
        versions.sort(key=key)
    except (ValueError, IndexError):
        pass
    return versions


def update_domain_registry(domain: str) -> None:
    """Update _registry.yaml for a domain from current tool directories."""
    base = get_tools_base_dir()
    domain_dir = base / domain
    if not domain_dir.exists():
        return
    tools = []
    for tool_dir in domain_dir.iterdir():
        if not tool_dir.is_dir() or tool_dir.name.startswith("_"):
            continue
        tool_id = tool_dir.name
        latest = get_latest_version(domain, tool_id)
        if latest:
            tools.append({
                "tool_id": tool_id,
                "current_version": latest,
                "latest_version": latest,
                "status": "active",
            })
    registry = {
        "domain": domain,
        "description": f"{domain.title()} domain tools",
        "tools": tools,
    }
    registry_path = get_domain_registry_path(domain)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "w") as f:
        yaml.dump(registry, f, default_flow_style=False, sort_keys=False)


def update_global_registry() -> None:
    """Update _global_registry.yaml with all domains."""
    base = get_tools_base_dir()
    if not base.exists():
        return
    domains = {}
    for domain_dir in base.iterdir():
        if not domain_dir.is_dir() or domain_dir.name.startswith("_"):
            continue
        domain = domain_dir.name
        count = sum(1 for t in domain_dir.iterdir() if t.is_dir() and not t.name.startswith("_"))
        domains[domain] = {
            "path": f"{domain}/",
            "description": f"{domain.title()} domain tools",
            "tool_count": count,
        }
    registry = {"domains": domains}
    with open(get_global_registry_path(), "w") as f:
        yaml.dump(registry, f, default_flow_style=False, sort_keys=False)


def list_domains() -> list[dict[str, Any]]:
    """List all domains with tool counts (from versioned storage)."""
    base = get_tools_base_dir()
    if not base.exists():
        return []
    out = []
    for domain_dir in sorted(base.iterdir()):
        if not domain_dir.is_dir() or domain_dir.name.startswith("_"):
            continue
        domain = domain_dir.name
        tools = []
        for tool_dir in domain_dir.iterdir():
            if not tool_dir.is_dir() or tool_dir.name.startswith("_"):
                continue
            latest = get_latest_version(domain, tool_dir.name)
            if latest:
                tools.append({"tool_id": tool_dir.name, "version": latest})
        out.append({
            "domain": domain,
            "description": f"{domain.title()} domain tools",
            "tool_count": len(tools),
            "tools": tools,
        })
    return out


def list_tools_in_domain(domain: str) -> list[dict[str, Any]]:
    """List all tools in a domain (latest version each)."""
    result = []
    base = get_tools_base_dir() / domain
    if not base.exists():
        return result
    for tool_dir in sorted(base.iterdir()):
        if not tool_dir.is_dir() or tool_dir.name.startswith("_"):
            continue
        tool_id = tool_dir.name
        latest = load_tool_latest(domain, tool_id)
        if latest:
            result.append(latest)
    return result


def migrate_flat_registry_to_versioned(get_tool_registry_path_fn, load_tools_fn) -> int:
    """
    One-time migration: read tool_registry.yaml and write versioned files.
    Returns number of tools migrated.
    """
    data = load_tools_fn()
    tools = data.get("tools") or {}
    count = 0
    for tool_name, tool_def in tools.items():
        domain = TOOL_DOMAIN_MAP.get(tool_name, "general")
        existing = load_tool_latest(domain, tool_name)
        if existing:
            continue
        save_tool_version(domain, tool_name, "1.0.0", tool_def, created_by="migration")
        update_tool_changelog(
            domain, tool_name, "1.0.0", None,
            {"initial": ["Initial version from tool_registry.yaml"]},
            created_by="migration",
        )
        count += 1
    for domain in {TOOL_DOMAIN_MAP.get(t, "general") for t in tools}:
        update_domain_registry(domain)
    update_global_registry()
    return count
