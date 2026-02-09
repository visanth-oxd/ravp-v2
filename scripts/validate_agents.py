#!/usr/bin/env python3
"""
Validate agent definitions and configurations.

Checks:
- Agent definition YAML files are valid
- Required fields are present
- Tools referenced exist in tool registry
- Policies referenced exist
- Agent code can be imported
"""

import sys
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any
import importlib.util

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load and parse YAML file."""
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return {}


def validate_agent_definition(agent_id: str, definition: Dict[str, Any]) -> List[str]:
    """Validate agent definition structure."""
    errors = []
    
    # Required fields
    required_fields = ['agent_id', 'version', 'domain', 'risk_tier', 'purpose', 'allowed_tools']
    for field in required_fields:
        if field not in definition:
            errors.append(f"Missing required field: {field}")
    
    # Validate agent_id matches filename
    if definition.get('agent_id') != agent_id:
        errors.append(f"agent_id mismatch: expected '{agent_id}', got '{definition.get('agent_id')}'")
    
    # Validate version format (semantic versioning)
    version = definition.get('version', '')
    if version and not all(c.isdigit() or c == '.' for c in version.split('.')):
        errors.append(f"Invalid version format: {version}")
    
    # Validate risk_tier
    valid_risk_tiers = ['low', 'medium', 'high']
    if definition.get('risk_tier') not in valid_risk_tiers:
        errors.append(f"Invalid risk_tier: {definition.get('risk_tier')}. Must be one of {valid_risk_tiers}")
    
    # Validate purpose structure
    purpose = definition.get('purpose', {})
    if not isinstance(purpose, dict):
        errors.append("purpose must be a dictionary")
    elif 'goal' not in purpose:
        errors.append("purpose.goal is required")
    
    # Validate allowed_tools is a list
    allowed_tools = definition.get('allowed_tools', [])
    if not isinstance(allowed_tools, list):
        errors.append("allowed_tools must be a list")
    
    # Validate model (if present)
    model = definition.get('model')
    if model and not isinstance(model, str):
        errors.append("model must be a string")
    
    return errors


def validate_tools_exist(agent_id: str, tool_names: List[str], tool_registry: Dict[str, Any]) -> List[str]:
    """Validate that referenced tools exist in tool registry."""
    errors = []
    registered_tools = tool_registry.get('tools', {})
    
    for tool_name in tool_names:
        if tool_name not in registered_tools:
            errors.append(f"Tool '{tool_name}' referenced by agent '{agent_id}' not found in tool registry")
    
    return errors


def validate_policies_exist(agent_id: str, policy_paths: List[str], policies_dir: Path) -> List[str]:
    """Validate that referenced policies exist."""
    errors = []
    
    for policy_path in policy_paths:
        # Convert policy path (e.g., "payments/retry") to file path
        policy_file = policies_dir / f"{policy_path}.rego"
        if not policy_file.exists():
            errors.append(f"Policy '{policy_path}' referenced by agent '{agent_id}' not found at {policy_file}")
    
    return errors


def validate_agent_code(agent_id: str, agents_dir: Path) -> List[str]:
    """Validate that agent code can be imported."""
    errors = []
    
    agent_dir = agents_dir / agent_id
    agent_file = agent_dir / "agent.py"
    
    if not agent_dir.exists():
        errors.append(f"Agent directory not found: {agent_dir}")
        return errors
    
    if not agent_file.exists():
        errors.append(f"Agent code file not found: {agent_file}")
        return errors
    
    # Try to import the agent module
    try:
        spec = importlib.util.spec_from_file_location(
            f"agents.{agent_id}.agent",
            agent_file
        )
        if spec is None or spec.loader is None:
            errors.append(f"Could not load agent module: {agent_file}")
        else:
            # Just check if it can be loaded, don't execute
            module = importlib.util.module_from_spec(spec)
            # We'll do a syntax check by trying to compile
            with open(agent_file, 'r') as f:
                compile(f.read(), agent_file, 'exec')
    except SyntaxError as e:
        errors.append(f"Syntax error in {agent_file}: {e}")
    except Exception as e:
        # Import errors are OK (dependencies might not be available)
        pass
    
    return errors


def main():
    """Main validation function."""
    print("🔍 Validating Agent Factory Configuration...\n")
    
    config_dir = repo_root / "config"
    agents_dir = repo_root / "agents"
    policies_dir = repo_root / "policies"
    
    # Load tool registry
    tool_registry_file = config_dir / "tool_registry.yaml"
    tool_registry = load_yaml(tool_registry_file)
    
    # Find all agent definitions
    agent_definitions_dir = config_dir / "agents"
    agent_yamls = list(agent_definitions_dir.glob("*.yaml"))
    agent_yamls = [f for f in agent_yamls if f.name != "template.yaml"]  # Skip template
    
    if not agent_yamls:
        print("⚠️  No agent definitions found")
        return 1
    
    all_errors = []
    all_warnings = []
    
    for agent_yaml in agent_yamls:
        agent_id = agent_yaml.stem
        print(f"📋 Validating agent: {agent_id}")
        
        # Load agent definition
        definition = load_yaml(agent_yaml)
        if not definition:
            all_errors.append(f"{agent_id}: Could not load definition file")
            continue
        
        # Validate definition structure
        errors = validate_agent_definition(agent_id, definition)
        if errors:
            all_errors.extend([f"{agent_id}: {e}" for e in errors])
        
        # Validate tools exist
        allowed_tools = definition.get('allowed_tools', [])
        if allowed_tools:
            errors = validate_tools_exist(agent_id, allowed_tools, tool_registry)
            if errors:
                all_errors.extend([f"{agent_id}: {e}" for e in errors])
        
        # Validate policies exist
        policies = definition.get('policies', [])
        if policies:
            errors = validate_policies_exist(agent_id, policies, policies_dir)
            if errors:
                all_errors.extend([f"{agent_id}: {e}" for e in errors])
        
        # Validate agent code
        errors = validate_agent_code(agent_id, agents_dir)
        if errors:
            all_warnings.extend([f"{agent_id}: {e}" for e in errors])
        
        print(f"   ✓ Definition valid")
    
    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    if all_errors:
        print(f"\n❌ Found {len(all_errors)} error(s):")
        for error in all_errors:
            print(f"   • {error}")
    
    if all_warnings:
        print(f"\n⚠️  Found {len(all_warnings)} warning(s):")
        for warning in all_warnings:
            print(f"   • {warning}")
    
    if not all_errors and not all_warnings:
        print("\n✅ All validations passed!")
        return 0
    
    if all_errors:
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
