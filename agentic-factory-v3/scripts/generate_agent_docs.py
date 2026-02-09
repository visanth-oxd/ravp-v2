#!/usr/bin/env python3
"""
Generate documentation for all agents.

Creates markdown documentation from agent definitions.
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, Any

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load YAML file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


def generate_agent_doc(agent_id: str, definition: Dict[str, Any], output_dir: Path):
    """Generate documentation for a single agent."""
    output_file = output_dir / f"{agent_id}.md"
    
    with open(output_file, 'w') as f:
        f.write(f"# {agent_id.replace('_', ' ').title()} Agent\n\n")
        
        # Basic info
        f.write("## Overview\n\n")
        f.write(f"**Agent ID**: `{agent_id}`\n")
        f.write(f"**Version**: {definition.get('version', 'N/A')}\n")
        f.write(f"**Domain**: {definition.get('domain', 'N/A')}\n")
        f.write(f"**Risk Tier**: {definition.get('risk_tier', 'N/A')}\n\n")
        
        # Purpose
        purpose = definition.get('purpose', {})
        if purpose:
            f.write("## Purpose\n\n")
            f.write(f"**Goal**: {purpose.get('goal', 'N/A')}\n\n")
            if purpose.get('instructions_prefix'):
                f.write("**Instructions**:\n\n")
                f.write(f"{purpose['instructions_prefix']}\n\n")
        
        # Owners
        owners = definition.get('owners', {})
        if owners:
            f.write("## Owners\n\n")
            for role, name in owners.items():
                f.write(f"- **{role.title()}**: {name}\n")
            f.write("\n")
        
        # Tools
        allowed_tools = definition.get('allowed_tools', [])
        if allowed_tools:
            f.write("## Allowed Tools\n\n")
            for tool in allowed_tools:
                f.write(f"- `{tool}`\n")
            f.write("\n")
        
        # Policies
        policies = definition.get('policies', [])
        if policies:
            f.write("## Policies\n\n")
            for policy in policies:
                f.write(f"- `{policy}`\n")
            f.write("\n")
        
        # Configuration
        f.write("## Configuration\n\n")
        f.write(f"- **Model**: {definition.get('model', 'N/A')}\n")
        f.write(f"- **Confidence Threshold**: {definition.get('confidence_threshold', 'N/A')}\n")
        f.write(f"- **Human in the Loop**: {definition.get('human_in_the_loop', False)}\n")


def main():
    """Generate documentation for all agents."""
    print("📚 Generating agent documentation...\n")
    
    config_dir = repo_root / "config" / "agents"
    output_dir = repo_root / "docs" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    agent_yamls = list(config_dir.glob("*.yaml"))
    agent_yamls = [f for f in agent_yamls if f.name != "template.yaml"]
    
    for agent_yaml in agent_yamls:
        agent_id = agent_yaml.stem
        definition = load_yaml(agent_yaml)
        generate_agent_doc(agent_id, definition, output_dir)
        print(f"✓ Generated docs for {agent_id}")
    
    print(f"\n✅ Documentation generated in {output_dir}")


if __name__ == "__main__":
    main()
