"""Agent versioning logic - automatically bump versions based on changes."""

from typing import Any, Dict, List, Tuple
import re


def parse_version(version: str) -> Tuple[int, int, int]:
    """
    Parse semantic version string into (major, minor, patch).
    
    Args:
        version: Version string like "1.2.3"
    
    Returns:
        Tuple of (major, minor, patch)
    """
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)
    if not match:
        raise ValueError(f"Invalid version format: {version}. Expected MAJOR.MINOR.PATCH")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def format_version(major: int, minor: int, patch: int) -> str:
    """Format version tuple to string."""
    return f"{major}.{minor}.{patch}"


def compare_lists(old_list: List[str], new_list: List[str]) -> Dict[str, List[str]]:
    """
    Compare two lists and return what was added/removed.
    
    Returns:
        {"added": [...], "removed": [...]}
    """
    old_set = set(old_list or [])
    new_set = set(new_list or [])
    return {
        "added": sorted(list(new_set - old_set)),
        "removed": sorted(list(old_set - new_set))
    }


def detect_changes(old_def: Dict[str, Any], new_def: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect what changed between two agent definitions.
    
    Returns:
        Dict with change types and details:
        {
            "major": [...],      # Breaking changes
            "minor": [...],      # Capability changes (tools/policies)
            "patch": [...]      # Non-breaking changes
        }
    """
    changes = {
        "major": [],
        "minor": [],
        "patch": []
    }
    
    # MAJOR changes (breaking)
    if old_def.get("risk_tier") != new_def.get("risk_tier"):
        changes["major"].append(f"risk_tier changed: {old_def.get('risk_tier')} -> {new_def.get('risk_tier')}")
    
    old_goal = old_def.get("purpose", {}).get("goal", "") if isinstance(old_def.get("purpose"), dict) else str(old_def.get("purpose", ""))
    new_goal = new_def.get("purpose", {}).get("goal", "") if isinstance(new_def.get("purpose"), dict) else str(new_def.get("purpose", ""))
    if old_goal != new_goal:
        changes["major"].append(f"purpose.goal changed")
    
    old_domain = old_def.get("domain", "")
    new_domain = new_def.get("domain", "")
    if old_domain != new_domain:
        changes["major"].append(f"domain changed: {old_domain} -> {new_domain}")
    
    # MINOR changes (capability changes - tools/policies)
    old_tools = sorted(old_def.get("allowed_tools", []) or [])
    new_tools = sorted(new_def.get("allowed_tools", []) or [])
    tool_changes = compare_lists(old_tools, new_tools)
    if tool_changes["added"]:
        changes["minor"].append(f"tools added: {', '.join(tool_changes['added'])}")
    if tool_changes["removed"]:
        changes["minor"].append(f"tools removed: {', '.join(tool_changes['removed'])}")
    
    old_policies = sorted(old_def.get("policies", []) or [])
    new_policies = sorted(new_def.get("policies", []) or [])
    policy_changes = compare_lists(old_policies, new_policies)
    if policy_changes["added"]:
        changes["minor"].append(f"policies added: {', '.join(policy_changes['added'])}")
    if policy_changes["removed"]:
        changes["minor"].append(f"policies removed: {', '.join(policy_changes['removed'])}")
    
    # PATCH changes (non-breaking)
    if old_def.get("model") != new_def.get("model"):
        changes["patch"].append(f"model changed: {old_def.get('model')} -> {new_def.get('model')}")
    
    if old_def.get("confidence_threshold") != new_def.get("confidence_threshold"):
        changes["patch"].append(f"confidence_threshold changed: {old_def.get('confidence_threshold')} -> {new_def.get('confidence_threshold')}")
    
    if old_def.get("human_in_the_loop") != new_def.get("human_in_the_loop"):
        changes["patch"].append(f"human_in_the_loop changed: {old_def.get('human_in_the_loop')} -> {new_def.get('human_in_the_loop')}")
    
    old_instructions = old_def.get("purpose", {}).get("instructions_prefix", "") if isinstance(old_def.get("purpose"), dict) else ""
    new_instructions = new_def.get("purpose", {}).get("instructions_prefix", "") if isinstance(new_def.get("purpose"), dict) else ""
    if old_instructions != new_instructions:
        changes["patch"].append("instructions_prefix updated")
    
    if old_def.get("owners") != new_def.get("owners"):
        changes["patch"].append("owners updated")
    
    return changes


def calculate_new_version(old_version: str, changes: Dict[str, List[str]], auto_bump: bool = True) -> Tuple[str, Dict[str, List[str]]]:
    """
    Calculate new version based on changes detected.
    
    Args:
        old_version: Current version string (e.g., "1.2.3")
        changes: Changes dict from detect_changes()
        auto_bump: If True, automatically bump version. If False, return old_version.
    
    Returns:
        Tuple of (new_version_string, changes_summary)
    """
    if not auto_bump:
        return old_version, changes
    
    major, minor, patch = parse_version(old_version)
    
    # Determine version bump level
    if changes["major"]:
        major += 1
        minor = 0
        patch = 0
    elif changes["minor"]:
        minor += 1
        patch = 0
    elif changes["patch"]:
        patch += 1
    
    new_version = format_version(major, minor, patch)
    
    # Create summary
    summary = {}
    if changes["major"]:
        summary["major"] = changes["major"]
    if changes["minor"]:
        summary["minor"] = changes["minor"]
    if changes["patch"]:
        summary["patch"] = changes["patch"]
    
    return new_version, summary


def create_changelog_entry(old_version: str, new_version: str, changes: Dict[str, List[str]], user: str = None) -> Dict[str, Any]:
    """
    Create a changelog entry for version history.
    
    Returns:
        Changelog entry dict
    """
    from datetime import datetime
    
    return {
        "version": new_version,
        "previous_version": old_version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "changes": changes,
        "changed_by": user
    }
