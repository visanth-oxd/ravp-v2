#!/usr/bin/env python3
"""
Test script for Agent Registry.
Run this to verify the agent registry is working.
"""

import sys
from pathlib import Path

# Add control-plane to path
repo_root = Path(__file__).resolve().parent.parent
control_plane = repo_root / "control-plane"
if str(control_plane) not in sys.path:
    sys.path.insert(0, str(control_plane))

from agent_registry.storage import load_agent, list_agents


def test_list_agents():
    """Test listing all agents."""
    print("=" * 60)
    print("Testing: List Agents")
    print("=" * 60)
    
    agents = list_agents()
    print(f"Found {len(agents)} agent(s):")
    for agent in agents:
        print(f"  - {agent['agent_id']} (v{agent['version']})")
    print()


def test_load_agent():
    """Test loading a specific agent."""
    print("=" * 60)
    print("Testing: Load Agent")
    print("=" * 60)
    
    agent_id = "payment_failed"
    definition = load_agent(agent_id)
    
    if definition:
        print(f"✅ Successfully loaded: {agent_id}")
        print(f"\nAgent Definition:")
        print(f"  ID: {definition.get('agent_id')}")
        print(f"  Version: {definition.get('version')}")
        print(f"  Domain: {definition.get('domain')}")
        print(f"  Risk Tier: {definition.get('risk_tier')}")
        print(f"  Purpose: {definition.get('purpose', {}).get('goal', 'N/A')}")
        print(f"  Allowed Tools: {', '.join(definition.get('allowed_tools', []))}")
        print(f"  Model: {definition.get('model', 'N/A')}")
    else:
        print(f"❌ Failed to load: {agent_id}")
    print()


if __name__ == "__main__":
    print("\n🧪 Testing Agent Registry\n")
    
    test_list_agents()
    test_load_agent()
    
    print("=" * 60)
    print("✅ Tests complete!")
    print("=" * 60)
