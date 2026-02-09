"""Tool versioning: detect changes and compute new version (MAJOR.MINOR.PATCH)."""

from typing import Any, Dict, List, Tuple
import re


def parse_version(version: str) -> Tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)
    if not match:
        raise ValueError(f"Invalid version format: {version}. Expected MAJOR.MINOR.PATCH")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def format_version(major: int, minor: int, patch: int) -> str:
    return f"{major}.{minor}.{patch}"


def _compare_lists(old_list: List[str], new_list: List[str]) -> Dict[str, List[str]]:
    old_set = set(old_list or [])
    new_set = set(new_list or [])
    return {
        "added": sorted(list(new_set - old_set)),
        "removed": sorted(list(old_set - new_set)),
    }


def detect_tool_changes(old_def: Dict[str, Any], new_def: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Detect what changed between two tool definitions.
    Returns: {"major": [...], "minor": [...], "patch": [...]}
    """
    changes: Dict[str, List[str]] = {"major": [], "minor": [], "patch": []}

    # MAJOR: risk_tier, requires_human_approval (behavior change)
    if old_def.get("risk_tier") != new_def.get("risk_tier"):
        changes["major"].append(
            f"risk_tier: {old_def.get('risk_tier')} -> {new_def.get('risk_tier')}"
        )
    if old_def.get("requires_human_approval") != new_def.get("requires_human_approval"):
        changes["major"].append("requires_human_approval changed")

    # MINOR: data_sources, pii_level
    ds_old = sorted(old_def.get("data_sources") or [])
    ds_new = sorted(new_def.get("data_sources") or [])
    if ds_old != ds_new:
        changes["minor"].append("data_sources changed")
    if old_def.get("pii_level") != new_def.get("pii_level"):
        changes["minor"].append(f"pii_level: {old_def.get('pii_level')} -> {new_def.get('pii_level')}")

    # PATCH: description only
    if (old_def.get("description") or "") != (new_def.get("description") or ""):
        changes["patch"].append("description updated")

    return changes


def calculate_new_tool_version(
    old_version: str, changes: Dict[str, List[str]], auto_bump: bool = True
) -> Tuple[str, Dict[str, List[str]]]:
    """Calculate new semantic version from changes. Returns (new_version, changes)."""
    if not auto_bump:
        return old_version, changes
    major, minor, patch = parse_version(old_version)
    if changes["major"]:
        major += 1
        minor = 0
        patch = 0
    elif changes["minor"]:
        minor += 1
        patch = 0
    elif changes["patch"]:
        patch += 1
    return format_version(major, minor, patch), changes
